import os
import sys
import subprocess
import urllib.request
import zipfile
import tarfile
import argparse
import platform
import shutil
import random
import string
import re
import xml.sax.saxutils
from pathlib import Path


AGP_VERSION = "8.2.0"
KOTLIN_VERSION = "1.9.20"
GRADLE_VERSION = "8.5"
COMPILE_SDK = 34
MIN_SDK = 19
TARGET_SDK = 34


CMDLINE_TOOLS_URLS = {
    "win32": "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip",
    "linux": "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip",
    "linux_aarch64": "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip",
    "darwin": "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
}


JDK_URLS = {
    "win32": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.zip",
    "linux": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_linux_hotspot_17.0.10_7.tar.gz",
    "linux_aarch64": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_aarch64_linux_hotspot_17.0.10_7.tar.gz",
    "darwin_x86_64": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_mac_hotspot_17.0.10_7.tar.gz",
    "darwin_arm64": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_aarch64_mac_hotspot_17.0.10_7.tar.gz"
}


GRADLE_URL = f"https://services.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip"


SETTINGS_GRADLE = """
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "WebViewApp"
include ':app'
"""


PROJECT_BUILD_GRADLE = f"""
plugins {{
    id 'com.android.application' version '{AGP_VERSION}' apply false
    id 'org.jetbrains.kotlin.android' version '{KOTLIN_VERSION}' apply false
}}
"""


def validate_inputs(app_name: str, package_name: str):
    if not app_name or not app_name.strip():
        raise ValueError("Error: App name cannot be empty or consist only of whitespace.")
    
    pkg_regex = r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$'
    if not re.match(pkg_regex, package_name):
        raise ValueError(f"Error: Invalid package name '{package_name}'. It must have at least two segments (e.g., com.example), start with a letter, and contain only alphanumeric characters and underscores.")


def escape_gradle_str(text: str) -> str:
    if not text:
        return ""
    return str(text).replace('\\', '\\\\').replace('"', '\\"')


def get_app_build_gradle(package_name: str, keystore_info: dict) -> str:
    keystore_path = escape_gradle_str(str(keystore_info['file']).replace('\\', '/'))
    storepass = escape_gradle_str(keystore_info['storepass'])
    alias = escape_gradle_str(keystore_info['alias'])
    keypass = escape_gradle_str(keystore_info['keypass'])
    
    return f"""
plugins {{
    id 'com.android.application'
    id 'org.jetbrains.kotlin.android'
}}


android {{
    namespace '{package_name}'
    compileSdk {COMPILE_SDK}


    defaultConfig {{
        applicationId "{package_name}"
        minSdk {MIN_SDK}
        targetSdk {TARGET_SDK}
        versionCode 1
        versionName "1.0"
        resConfigs "en"
    }}


    signingConfigs {{
        release {{
            storeFile file("{keystore_path}")
            storePassword "{storepass}"
            keyAlias "{alias}"
            keyPassword "{keypass}"
        }}
    }}


    buildTypes {{
        release {{
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt')
            signingConfig signingConfigs.release
        }}
    }}
    
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
}}


dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
}}
"""


def get_manifest(app_name: str, icon_ref: str) -> str:
    safe_app_name = xml.sax.saxutils.escape(app_name, {"'": "&apos;", '"': "&quot;"})
    
    return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <application
        android:allowBackup="true"
        android:icon="{icon_ref}"
        android:label="{safe_app_name}"
        android:supportsRtl="true"
        android:usesCleartextTraffic="true"
        android:theme="@style/Theme.AppCompat.DayNight.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|keyboardHidden|screenSize"
            android:windowSoftInputMode="adjustNothing"
            android:theme="@style/Theme.AppCompat.DayNight.NoActionBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""


def get_main_activity(package_name: str, entry_point: str) -> str:
    return f"""package {package_name}


import android.content.res.Configuration
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity


class MainActivity : AppCompatActivity() {{
    private lateinit var webView: WebView


    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)


        webView = WebView(this)
        val settings = webView.settings
        
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.allowFileAccess = true
        settings.allowFileAccessFromFileURLs = true
        settings.allowUniversalAccessFromFileURLs = true
        settings.mediaPlaybackRequiresUserGesture = false

        val isNightMode = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {{
            settings.isAlgorithmicDarkeningAllowed = isNightMode
        }}

        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
        if (isNightMode) {{
            window.statusBarColor = Color.BLACK
        }} else {{
            window.statusBarColor = Color.WHITE
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {{
                window.insetsController?.setSystemBarsAppearance(
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS,
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                )
            }} else {{
                @Suppress("DEPRECATION")
                window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
            }}
        }}


        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()


        setContentView(webView)
        webView.loadUrl("file:///android_asset/{entry_point}")
    }}


    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {{
        if (webView.canGoBack()) {{
            webView.goBack()
        }} else {{
            super.onBackPressed()
        }}
    }}
    
    override fun onResume() {{
        super.onResume()
        webView.onResume()
    }}

    override fun onPause() {{
        super.onPause()
        webView.onPause()
    }}

    override fun onDestroy() {{
        webView.destroy()
        super.onDestroy()
    }}
}}
"""


def download_with_progress(url, dest_path):
    print(f"[*] Downloading {url.split('/')[-1]}...")
    def reporthook(blocknum, blocksize, totalsize):
        readsofar = blocknum * blocksize
        if totalsize > 0:
            percent = readsofar * 1e2 / totalsize
            s = f"\r{percent:5.1f}% {readsofar / 1024 / 1024:.1f} MB / {totalsize / 1024 / 1024:.1f} MB"
            sys.stdout.write(s)
            if readsofar >= totalsize:
                sys.stdout.write("\n")
        else:
            sys.stdout.write(f"\r{readsofar} bytes read")
    urllib.request.urlretrieve(url, dest_path, reporthook)


def setup_java(workspace: Path) -> Path:
    java_dir = workspace / "java"
    java_dir.mkdir(parents=True, exist_ok=True)
    
    os_name = sys.platform
    machine = platform.machine().lower()
    
    if os_name == "darwin":
        key = "darwin_arm64" if "arm" in machine or "aarch" in machine else "darwin_x86_64"
    elif os_name == "linux":
        key = "linux_aarch64" if "arm" in machine or "aarch" in machine else "linux"
    else:
        key = os_name
        
    jdk_url = JDK_URLS.get(key, JDK_URLS["linux"])
    is_zip = jdk_url.endswith(".zip")
    archive_name = "jdk.zip" if is_zip else "jdk.tar.gz"
    archive_path = workspace / archive_name
    
    extracted_dirs = [d for d in java_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    if not extracted_dirs:
        download_with_progress(jdk_url, archive_path)
        print("[*] Extracting OpenJDK...")
        if is_zip:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(java_dir)
        else:
            with tarfile.open(archive_path, 'r:gz') as tf:
                tf.extractall(java_dir)
        
        extracted_dirs = [d for d in java_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if archive_path.exists():
            archive_path.unlink()
            
    base_dir = extracted_dirs[0]
    
    if os_name == "darwin":
        java_home = base_dir / "Contents" / "Home"
        if not java_home.exists():
            java_home = base_dir
    else:
        java_home = base_dir
        
    print(f"[*] Local Java Home configured: {java_home}")
    return java_home


def setup_environment(workspace: Path, java_home: Path):
    os_name = sys.platform
    machine = platform.machine().lower()
    
    if os_name == "linux":
        cmdline_key = "linux_aarch64" if "arm" in machine or "aarch" in machine else "linux"
    else:
        cmdline_key = os_name
        
    cmdline_url = CMDLINE_TOOLS_URLS.get(cmdline_key, CMDLINE_TOOLS_URLS["linux"])
    
    sdk_dir = workspace / "android_sdk"
    gradle_dir = workspace / "gradle"
    
    sdk_dir.mkdir(parents=True, exist_ok=True)
    gradle_dir.mkdir(parents=True, exist_ok=True)
    
    cmdline_zip = workspace / "cmdline-tools.zip"
    gradle_zip = workspace / "gradle.zip"
    
    cmdline_latest_dir = sdk_dir / "cmdline-tools" / "latest"
    if not cmdline_latest_dir.exists():
        download_with_progress(cmdline_url, cmdline_zip)
        print("[*] Extracting Android Command Line Tools...")
        with zipfile.ZipFile(cmdline_zip, 'r') as zip_ref:
            zip_ref.extractall(sdk_dir / "cmdline-tools")
        
        extracted_dir = sdk_dir / "cmdline-tools" / "cmdline-tools"
        if extracted_dir.exists():
            extracted_dir.rename(cmdline_latest_dir)
            
    sdkmanager_bin = "sdkmanager.bat" if os.name == "nt" else "sdkmanager"
    sdkmanager_path = cmdline_latest_dir / "bin" / sdkmanager_bin
    
    if os.name != "nt":
        os.chmod(sdkmanager_path, 0o755)


    print("[*] Accepting SDK Licenses and installing build-tools...")
    env = os.environ.copy()
    env["JAVA_HOME"] = str(java_home.absolute())
    
    subprocess.run([str(sdkmanager_path), "--licenses"], input=b"y\n" * 50, env=env, stdout=subprocess.DEVNULL)
    subprocess.run([str(sdkmanager_path), f"platforms;android-{COMPILE_SDK}", "build-tools;34.0.0"], env=env, check=True)


    gradle_bin_dir = gradle_dir / f"gradle-{GRADLE_VERSION}"
    if not gradle_bin_dir.exists():
        download_with_progress(GRADLE_URL, gradle_zip)
        print("[*] Extracting Gradle...")
        with zipfile.ZipFile(gradle_zip, 'r') as zip_ref:
            zip_ref.extractall(gradle_dir)
            
    gradle_bin = "gradle.bat" if os.name == "nt" else "gradle"
    gradle_path = gradle_bin_dir / "bin" / gradle_bin
    
    if os.name != "nt":
        os.chmod(gradle_path, 0o755)


    return sdk_dir, gradle_path


def create_project_structure(project_dir: Path, input_path: Path, app_name: str, package_name: str, icon_path: Path, entry_point: str, keystore_info: dict):
    print(f"[*] Generating Android project (App: '{app_name}', Package: '{package_name}')...")
    app_dir = project_dir / "app"
    src_main = app_dir / "src" / "main"
    
    java_dir = src_main.joinpath("java", *package_name.split('.'))
    assets_dir = src_main / "assets"
    
    for d in [java_dir, assets_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    (project_dir / "settings.gradle").write_text(SETTINGS_GRADLE, encoding="utf-8")
    (project_dir / "build.gradle").write_text(PROJECT_BUILD_GRADLE, encoding="utf-8")
    (project_dir / "gradle.properties").write_text("org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\n", encoding="utf-8")
    
    (app_dir / "build.gradle").write_text(get_app_build_gradle(package_name, keystore_info), encoding="utf-8")
    (java_dir / "MainActivity.kt").write_text(get_main_activity(package_name, entry_point), encoding="utf-8")
    
    icon_ref = "@android:drawable/sym_def_app_icon"
    if icon_path and icon_path.exists():
        ext = icon_path.suffix.lower()
        if ext in {'.png', '.webp', '.jpg', '.jpeg'}:
            mipmap_dir = src_main / "res" / "mipmap-xxhdpi"
            mipmap_dir.mkdir(parents=True, exist_ok=True)
            icon_filename = f"ic_launcher{ext}"
            shutil.copy(icon_path, mipmap_dir / icon_filename)
            icon_ref = "@mipmap/ic_launcher"
        else:
            raise ValueError(f"Error: Unsupported icon format '{ext}'. Android supports PNG, WEBP, JPG, and JPEG for mipmap launcher icons.")
    elif icon_path:
        print(f"[!] Warning: Icon {icon_path} not found. Falling back to default icon.")
        
    (src_main / "AndroidManifest.xml").write_text(get_manifest(app_name, icon_ref), encoding="utf-8")
    
    print("[*] Copying web assets...")
    if input_path.is_file():
        shutil.copy(input_path, assets_dir / entry_point)
    elif input_path.is_dir():
        shutil.copytree(input_path, assets_dir, dirs_exist_ok=True)
        if not (assets_dir / entry_point).exists():
            print(f"[!] Warning: Entry point '{entry_point}' not found in the root of the provided folder.")


def generate_temp_keystore(keystore_path: Path, java_home: Path):
    print("[*] Generating temporary keystore for signing...")
    keytool_bin = "keytool.exe" if os.name == "nt" else "keytool"
    keytool_path = java_home / "bin" / keytool_bin
    
    if keystore_path.exists():
        keystore_path.unlink()
        
    subprocess.run([
        str(keytool_path), "-genkey", "-v",
        "-keystore", str(keystore_path),
        "-alias", "tempalias",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "1",
        "-storepass", "temp1234", "-keypass", "temp1234",
        "-dname", "CN=Temp,O=Temp,C=US"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_apk(project_dir: Path, sdk_dir: Path, gradle_path: Path, output_apk: Path, java_home: Path, is_temp_keystore: bool):
    app_dir = project_dir / "app"
    keystore_path = app_dir / "temp.keystore"
    
    if is_temp_keystore:
        generate_temp_keystore(keystore_path, java_home)


    print("[*] Starting Gradle Build (assembleRelease)...")
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(sdk_dir.absolute())
    env["JAVA_HOME"] = str(java_home.absolute())
    
    result = subprocess.run([str(gradle_path.absolute()), "assembleRelease", "--no-daemon", "--stacktrace"], 
                            cwd=str(project_dir), env=env)
    
    if is_temp_keystore and keystore_path.exists():
        print("[*] Discarding temporary keystore to prevent future overwrite installations...")
        keystore_path.unlink()


    if result.returncode != 0:
        print("[!] Build failed.")
        sys.exit(1)
        
    apk_source = project_dir / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
    if apk_source.exists():
        shutil.copy(apk_source, output_apk)
        print(f"\n[+] Success! APK saved to: {output_apk.absolute()}")
    else:
        print("[!] Output APK file not found.")


def main():
    parser = argparse.ArgumentParser(description="HTML/Web Folder to APK packager tool")
    parser.add_argument("input", help="Input HTML file or folder containing web assets")
    parser.add_argument("-o", "--output", default="app-release.apk", help="Output APK filename")
    parser.add_argument("-n", "--name", default="Web App", help="App name displayed on launcher (default: Web App)")
    parser.add_argument("-p", "--package", help="Package name (default: auto-generates com.example.<random>)")
    parser.add_argument("-i", "--icon", help="Path to custom PNG icon file")
    parser.add_argument("-e", "--entry", default="index.html", help="Entry point HTML file (default: index.html)")
    parser.add_argument("--keystore", help="Path to a custom .jks or .keystore signing file")
    parser.add_argument("--storepass", help="Keystore password")
    parser.add_argument("--alias", default="key0", help="Key alias")
    parser.add_argument("--keypass", help="Key password (if omitted, defaults to storepass)")

    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[!] Path not found: {input_path}")
        sys.exit(1)
        
    icon_path = Path(args.icon) if args.icon else None
    
    package_name = args.package
    if not package_name:
        random_str = ''.join(random.choices(string.ascii_lowercase, k=8))
        package_name = f"com.example.{random_str}"
        
    validate_inputs(args.name, package_name)
        
    if args.keystore:
        custom_keystore_path = Path(args.keystore).absolute()
        if not custom_keystore_path.exists():
            print(f"[!] Keystore not found: {custom_keystore_path}")
            sys.exit(1)
        if not args.storepass or not args.alias:
            print("[!] Error: When specifying --keystore, you must also provide --storepass and --alias.")
            sys.exit(1)
            
        keystore_info = {
            'file': custom_keystore_path,
            'storepass': args.storepass,
            'alias': args.alias,
            'keypass': args.keypass if args.keypass else args.storepass
        }
        is_temp_keystore = False
        print(f"[*] Using custom keystore for signing: {custom_keystore_path}")
    else:
        keystore_info = {
            'file': 'temp.keystore', 
            'storepass': 'temp1234',
            'alias': 'tempalias',
            'keypass': 'temp1234'
        }
        is_temp_keystore = True
        
    workspace = Path(".apk_build_env").absolute()
    project_dir = workspace / "project"
    
    workspace.mkdir(exist_ok=True)
    
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir()
    
    java_home = setup_java(workspace)
    sdk_dir, gradle_path = setup_environment(workspace, java_home)
    
    create_project_structure(
        project_dir=project_dir, 
        input_path=input_path, 
        app_name=args.name, 
        package_name=package_name, 
        icon_path=icon_path, 
        entry_point=args.entry,
        keystore_info=keystore_info
    )
    
    build_apk(project_dir, sdk_dir, gradle_path, Path(args.output), java_home, is_temp_keystore)


if __name__ == "__main__":
    main()
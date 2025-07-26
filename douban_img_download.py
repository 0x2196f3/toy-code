from playwright.sync_api import sync_playwright
import time
import os
import re
import urllib.parse

# Define the user script to be executed on the webpage
user_script_for_personage = r"""

/*jshint esversion: 8 */
(function () {
  `use strict`;

  var config_;

  const batchDownload = function () {
    let $imgList = document.querySelectorAll(config_.imgListSelector);
    // 验证预览图是否未加载
    if ($imgList.length == 0) {
      setTimeout(batchDownload, 1000);
      return;
    }

    const imgArr = [];
    $imgList.forEach(($img) => {
      // 获取图片信息
      const imgInf = getImgInfo($img);
      if (!imgInf) {
        return;
      }
      imgArr.push(imgInf);
    });

    // const subDomains = imgArr.map(m => m.subdomain).filter((item, index, arr) => arr.indexOf(item) === index);
    // let confirmToGo = true;
    // if (subDomains.length >= 1) {
    //   confirmToGo = confirm('图片中存在不同二级域名的地址, 因为安全限制可能只能自动下载部分图片, 是否继续?');
    // }
    // if (!confirmToGo) {
    //   return;
    // }

    for (let i=0; i < imgArr.length; i++) {
      const imgInf = imgArr[i];

      // 格式化原图下载链接
      let dlLink = document.createElement("a");
      dlLink.href = imgInf.raw;
      // dlLink.download = `${(config_.titlePrefix ? (config_.titlePrefix + '-') : '')}${(imgInf.subdomain ? (imgInf.subdomain + '-') : '')}${imgInf.id}.${config_.photoSrcExtension}`;
      dlLink.download = `${(config_.titlePrefix ? (config_.titlePrefix + '-') : '')}p${imgInf.id}.${config_.photoSrcExtension}`;

      GM_xmlhttpRequest({
        method: 'GET',
        url: dlLink.href,
        headers: {
          'Referer': 'https://www.douban.com/'
        },
        responseType: 'blob',
        onload: function(response) {
          if (response.status === 200) {
            const blob = response.response;
            const blobURL = URL.createObjectURL(blob);
            const downloadLink = document.createElement('a');
            downloadLink.href = blobURL;
            downloadLink.download = dlLink.download;

            downloadLink.click();

            URL.revokeObjectURL(blobURL);
            console.log(`picture downloaded: ${downloadLink.href}`);
          } else {
            console.error(`picture download failed: ${JSON.stringify(response)}`);
          }
        }
      });
    }
  }

  const init = function () {
    const domainRegex = /:\/\/([^.]+?)\.(?<domain>[\w\.]+)/;
    const configMap = {
      "douban.com": {
        // 批量下载链接容器
        "batchDownloadBtnContainerSelector": ".opt-bar-line",
        // 批量下载链接 css 类
        "batchDownloadBtnClass": "fright",
        "imgListSelector": "div.article ul li img",
        "subDomainRegex": /https?:\/\/(?<domain>[^.]+?)\..+/,
        "subDomainReplacement": "$<domain>",
        "photoIdRegex": /.+photo\/(?<id>\d+).*/,
        "photoIdReplacement": "$<id>",
        "photoSrcRegex": /(?<prefix>.+photo\/)\w+(?<suffix>\/public.+)\..*/,
        "photoSrcReplacement": "$<prefix>raw$<suffix>.jpg",
        "photoSrcExtension": "jpg",
        "photoClosestSelector": "li",
        // 单图下载链接容器
        "photoLinkContainerSelector": ".name",
        "titleSelector": "#wrapper #content h1",
        "titlePrefix": ""
      },
      "weibo.com": {
        "batchDownloadBtnContainerSelector": ".m_share_like",
        "batchDownloadBtnClass": undefined,
        "imgListSelector": "ul.photoList li img",
        "subDomainRegex": null,
        "subDomainReplacement": null,
        "photoIdRegex": /.+photo_id\/(?<id>\d+).*/,
        "photoIdReplacement": "$<id>",
        "photoSrcRegex": /(?<prefix>.+\/)\w+(?<suffix>\/.*)/,
        "photoSrcReplacement": "$<prefix>large$<suffix>",
        "photoClosestSelector": null,
        "photoLinkContainerSelector": null,
        "titleSelector": "",
        "titlePrefix": ""
      }
    };

    let domain = domainRegex.exec(document.location.origin).groups.domain;
    config_ = configMap[domain];
    if (!config_) {
      console.log('no works here');
    }

    let batchDownloadBtn = document.createElement("a");
    batchDownloadBtn.innerHTML = "批量下载本页原图 &#x1F608;";
    batchDownloadBtn.href = "javascript:;";
    batchDownloadBtn.style.fontWeight = "normal";
    batchDownloadBtn.style.marginRight = "10px";
    batchDownloadBtn.classList.add(config_.batchDownloadBtnClass);
    batchDownloadBtn.onclick = batchDownload;

    document.querySelector(config_.batchDownloadBtnContainerSelector).appendChild(batchDownloadBtn);

    // 附加原图链接
    if (!config_.photoClosestSelector || !config_.photoLinkContainerSelector) {
      return;
    }

    // 验证预览图是否未加载
    let $imgList = document.querySelectorAll(config_.imgListSelector);
    if ($imgList.length == 0) {
      return;
    }

    // 标题前缀
    if (config_.titleSelector) {
      const titleContainer = document.querySelector(config_.titleSelector);
      if (titleContainer) {
        config_.titlePrefix = titleContainer.innerHTML.split(' ')[0].replace('的图片', '');
      }
    }

    // 附加原图链接
    $imgList.forEach(($img) => {
      const imgInf = getImgInfo($img);
      if (!imgInf) {
        return;
      }

      const closestContainer = $img.closest(config_.photoClosestSelector);
      if (!closestContainer) {
        console.warn('preview image closest container not found');
        return;
      }

      const srcLinkContainer = closestContainer.querySelector(config_.photoLinkContainerSelector);
      if (!srcLinkContainer || !srcLinkContainer.innerHTML) {
        console.warn('src image container not found');
        return;
      }

      const srcText = srcLinkContainer.innerHTML;
      if (!srcText) {
        console.warn('src image container not found');
        return;
      }

      const rawUrl = imgInf.thumbnail.replace(config_.photoSrcRegex, config_.photoSrcReplacement);

      const srcLink = document.createElement("a");
      srcLink.innerHTML = `&#128194; 打开`; // ${imgInf.id}
      srcLink.href = rawUrl;
      srcLink.style.marginLeft = '5px';
      srcLink.setAttribute("target", "_blank");

      const dlLink = document.createElement("a");
      dlLink.innerHTML = `&#9196; 原图`; // &#x1F308;
      dlLink.href = rawUrl;
      dlLink.style.marginLeft = '5px';
      // dlLink.setAttribute("download", `${(config_.titlePrefix ? (config_.titlePrefix + '-') : '')}${(imgInf.subdomain ? (imgInf.subdomain + '-') : '')}${imgInf.id}.${config_.photoSrcExtension}`);
      dlLink.setAttribute("download", `${(config_.titlePrefix ? (config_.titlePrefix + '-') : '')}p${imgInf.id}.${config_.photoSrcExtension}`);

      srcLinkContainer.replaceChildren();
      srcLinkContainer.innerHTML = srcText;

      var pcntr = document.createElement('p');
      pcntr.style.margin = 0;
      pcntr.appendChild(srcLink);
      pcntr.appendChild(dlLink);
      srcLinkContainer.appendChild(pcntr);
      srcLinkContainer.appendChild(pcntr);
    });
  }

  const getImgInfo = function ($img) {
    if (!$img) {
      return null;
    }

    const src = $img.src;
    const refUrl = $img.parentNode.href;

    return {
      subdomain: config_.subDomainRegex && config_.subDomainReplacement
        ? src.replace(config_.subDomainRegex, config_.subDomainReplacement)
        : "",
      thumbnail: src,
      raw: src.replace(config_.photoSrcRegex, config_.photoSrcReplacement),
      refUrl: refUrl,
      id: refUrl.replace(config_.photoIdRegex, config_.photoIdReplacement)
    }
  }

  init();
})();

"""

user_script_for_album = r"""
(function () {
  `use strict`;

  var config_;

  const init = function () {
    const domainRegex = /:\/\/([^.]+?)\.(?<domain>[\w\.]+)/;
    const configMap = {
      "douban.com": {
        "imgListSelector": "div.article div.photolst",
        "subDomainRegex": /https?:\/\/(?<domain>[^.]+?)\..+/,
        "subDomainReplacement": "$<domain>",
        "photoIdRegex": /.+photo\/(?<id>\d+).*/,
        "photoIdReplacement": "$<id>",
        "photoSrcRegex": /(?<prefix>.+photo\/)\w+(?<suffix>\/public.+)\..*/,
        "photoSrcReplacement": "$<prefix>raw$<suffix>.jpg",
        "photoSrcExtension": "jpg",
        "photoClosestSelector": "div",
        // 单图下载链接容器
        "photoLinkContainerSelector": ".photolst_photo",
        "titleSelector": ".photolst_photo",
        "titlePrefix": ""
      },
    };

    let domain = domainRegex.exec(document.location.origin).groups.domain;
    config_ = configMap[domain];
    if (!config_) {
      console.log('no works here');
    }

    // 附加原图链接
    if (!config_.photoClosestSelector || !config_.photoLinkContainerSelector) {
      console.log("    if (!config_.photoClosestSelector || !config_.photoLinkContainerSelector) {");
      return;
    }

    // 验证预览图是否未加载
    let $imgList = document.querySelectorAll(config_.imgListSelector);
    if ($imgList.length == 0) {
      console.log("    if ($imgList.length == 0) {");
      return;
    }

    // 标题前缀
    if (config_.titleSelector) {
      const titleContainer = document.querySelector(config_.titleSelector);
      if (titleContainer) {
        config_.titlePrefix = titleContainer.innerHTML.split(' ')[0].replace('的图片', '');
      }
    }

    // 附加原图链接
    var imgList = document.querySelectorAll(config_.imgListSelector)[0];
    imgList = imgList.querySelectorAll("img");

    for (var i = 0; i < imgList.length; i++) {
      var img = imgList[i];
      const imgInf = getImgInfo(img);
      console.log(imgInf);
      if (!imgInf) {
        return;
      }

      const rawUrl = imgInf.thumbnail.replace(config_.photoSrcRegex, config_.photoSrcReplacement);

      var link = document.createElement('a');
      link.href = rawUrl;
      link.target = '_blank';
      link.innerHTML = `&#9196; 原图`;
      link.style.marginLeft = '5px';

      img.parentNode.appendChild(link);
    }
  }

  const getImgInfo = function (img) {
    if (!img) {
      return null;
    }

    const src = img.src;
    const refUrl = img.parentNode.href;

    return {
      subdomain: config_.subDomainRegex && config_.subDomainReplacement
        ? src.replace(config_.subDomainRegex, config_.subDomainReplacement)
        : "",
      thumbnail: src,
      raw: src.replace(config_.photoSrcRegex, config_.photoSrcReplacement),
      refUrl: refUrl,
      id: refUrl.replace(config_.photoIdRegex, config_.photoIdReplacement)
    }
  }

  init();
})();

"""

# Define the JavaScript code to get the image URLs
get_image_urls_script = r"""
const links = document.querySelectorAll('a');

const downloadLinks = [];

links.forEach(link => {
  if (link.textContent === '⏬ 原图') {
    // Get the href attribute
    const href = link.getAttribute('href');
    downloadLinks.push(`${href}\n`);
  }
});

downloadLinks;
"""

# Define the JavaScript code to download the image
download_image_script = r"""
var imageElement = document.querySelector('img');
if (imageElement) {
    var downloadLink = document.createElement('a');
    downloadLink.href = imageElement.src;
    downloadLink.download = document.URL.split('/').pop();
    downloadLink.click();
    setTimeout(function() {
        window.close();
    }, 10000);
}

"""

def url_to_filename(url):
    # Remove protocol part
    url = re.sub(r'^https?://', '', url)
    
    # Remove query parameters and fragments
    url = urllib.parse.urlparse(url).path
    
    # Replace special characters with underscores
    url = re.sub(r'[^a-zA-Z0-9._-]', '_', url)
    
    # Remove trailing slashes and dots
    url = re.sub(r'[._-]+$', '', url)
    
    return url


def main(base_url="https://www.douban.com/photos/album/1891135753/", total=103):
    print("main" + base_url + str(total))
    current_dir = os.path.dirname(os.path.abspath(__file__))

    download_path = os.path.join(current_dir, url_to_filename(base_url))
    if not os.path.exists(current_dir):
        try:
            # Create the current directory if it doesn't exist
            os.makedirs(current_dir, exist_ok=True)
        except PermissionError:
            print(f"Permission denied: unable to create directory '{current_dir}'")
            return None
        except OSError as e:
            print(f"Error creating directory '{current_dir}': {e}")
            return None
    
    # Check if the download path exists and is a directory
    if not os.path.exists(download_path):
        try:
            # Create the download path if it doesn't exist
            os.makedirs(download_path, exist_ok=True)
        except PermissionError:
            print(f"Permission denied: unable to create directory '{download_path}'")
            return None
        except OSError as e:
            print(f"Error creating directory '{download_path}': {e}")
            return None
    elif not os.path.isdir(download_path):
        print(f"'{download_path}' is not a directory")
        return None
        
    
    if "personage" in base_url:
        user_script = user_script_for_personage
        page_count = 30
        head = "?start="
        tail = "&sortby=like"
    elif "album" in base_url:
        user_script = user_script_for_album
        page_count = 18
        head= "?m_start="
        tail = ""
    else:
        print("NO USER_SCRIPT FOUND")
        return
    
    i = 0
    while i < total:
        print("i = " + str(i))
        with sync_playwright() as p:
            

            browser = p.chromium.launch(headless=False, downloads_path=download_path)
            context = browser.new_context()
                        
            page = context.new_page()

            # Navigate to the webpage
            page.goto(base_url + head + str(i) + tail)

            # Wait for the webpage to load
            page.wait_for_load_state("networkidle")

            # Execute the user script on the webpage
            
            page.evaluate(user_script)
            time.sleep(2)  # Wait for 2 seconds
            page.wait_for_load_state("networkidle")

            # Get the image URLs
            image_urls = page.evaluate(get_image_urls_script)
            time.sleep(2)  # Wait for 2 seconds
            page.wait_for_load_state("networkidle")

            # Download each image
            for url in image_urls:
                # Open the image URL in a new tab
                url = url.replace("\n", "")

                temp_js = r"""
                var link = document.createElement('a');
                link.href = '%s';
                link.target = '_blank';
                link.click();
                """ % url
                

                with context.expect_page() as new_page_info:
                    page.evaluate(temp_js)

                new_page = new_page_info.value
                page.wait_for_load_state("networkidle")

                time.sleep(2)  # Wait for 2 seconds

                new_page.evaluate(download_image_script)
                page.wait_for_load_state("networkidle")

                time.sleep(2)  # Wait for 2 seconds

                # Close the new tab
                new_page.close()

            # Close the browser
            browser.close()
        i = i + page_count

main("https://www.douban.com/personage/34441871/photos/", 588)
main("https://www.douban.com/photos/album/1903175452/", 38)
main("https://www.douban.com/photos/album/1905101314/", 69)
main("https://www.douban.com/photos/album/1905101255/", 74)
main("https://www.douban.com/photos/album/1896810559/", 45)
main("https://www.douban.com/photos/album/1903175382/", 47)
main("https://www.douban.com/photos/album/1905101159/", 99)
main("https://www.douban.com/photos/album/1905129748/", 55)
main("https://www.douban.com/photos/album/1905101214/", 100)
main("https://www.douban.com/photos/album/1905129595/", 85)
main("https://www.douban.com/photos/album/1905101177/", 98)
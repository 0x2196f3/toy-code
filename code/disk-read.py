import argparse
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("file_reader")

def iter_files(root: Path):
    for p in root.rglob("*"):
        try:
            if p.is_file():
                yield p
        except Exception as e:
            logger.debug("Skipping path due to error: %s (%s)", p, e)

def process_once(root: Path, chunk_size: int):
    start_time = time.time()
    file_count = 0
    bytes_read_total = 0

    logger.info("Starting pass over root=%s chunk_size=%d", root, chunk_size)
    devnull_path = os.devnull

    with open(devnull_path, "wb") as devnull:
        for file_path in iter_files(root):
            file_count += 1
            file_bytes = 0
            file_start = time.time()

            try:
                size = file_path.stat().st_size
            except Exception as e:
                size = None
                logger.debug("Could not stat file: %s (%s)", file_path, e)

            logger.info("Reading file %d: %s size=%s", file_count, file_path, size)

            try:
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        devnull.write(chunk)
                        file_bytes += len(chunk)
                        bytes_read_total += len(chunk)

                devnull.flush()
                elapsed = time.time() - file_start
                logger.info(
                    "Finished file %d: %s bytes=%d elapsed=%.3fs",
                    file_count,
                    file_path,
                    file_bytes,
                    elapsed,
                )
            except Exception as e:
                logger.warning("Failed reading file %d: %s (%s)", file_count, file_path, e)
                continue

    total_elapsed = time.time() - start_time
    logger.info(
        "Completed pass root=%s files=%d bytes=%d elapsed=%.3fs",
        root,
        file_count,
        bytes_read_total,
        total_elapsed,
    )

def main():
    parser = argparse.ArgumentParser(description="Read all files into memory and drop to os.devnull (streaming).")
    parser.add_argument("--count", type=int, default=1, help="How many times to read all files (default: 1)")
    parser.add_argument("--chunk-size", type=int, default=1024 * 1024, help="Read chunk size in bytes (default 1MiB)")
    parser.add_argument("--log-level", default="INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        script_dir = Path(__file__).resolve().parent
        logger.debug("Resolved script_dir from __file__: %s", script_dir)
    except NameError:
        script_dir = Path.cwd()
        logger.debug("__file__ unavailable, using cwd as script_dir: %s", script_dir)

    os.chdir(str(script_dir))
    logger.info("Working directory set to %s", script_dir)

    iterations = max(1, args.count)
    logger.info("Starting %d iteration(s)", iterations)

    for i in range(iterations):
        logger.info("Beginning iteration %d of %d", i + 1, iterations)
        process_once(Path.cwd(), args.chunk_size)
        logger.info("Finished iteration %d of %d", i + 1, iterations)

if __name__ == "__main__":
    main()
    input("Press Any Key To Continue")

import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def mismatching_chunks(path1="./1.mp4", path2="./2.mp4", chunk_size=1024):
    mismatches = []

    path1 = Path(path1)
    path2 = Path(path2)

    logging.info("Starting file comparison")
    logging.info("File 1: %s", path1.resolve())
    logging.info("File 2: %s", path2.resolve())
    logging.info("Chunk size: %d bytes", chunk_size)

    with path1.open("rb") as f1, path2.open("rb") as f2:
        index = 0

        while True:
            c1 = f1.read(chunk_size)
            c2 = f2.read(chunk_size)

            if not c1 and not c2:
                logging.info("Reached end of both files at chunk %d", index)
                break

            logging.debug(
                "Chunk %d | file1=%d bytes | file2=%d bytes",
                index, len(c1), len(c2)
            )

            if c1 != c2:
                logging.warning(
                    "Mismatch at chunk %d | file1=%d bytes | file2=%d bytes",
                    index, len(c1), len(c2)
                )
                mismatches.append(index)

            index += 1

    logging.info("Comparison finished")
    logging.info("Total mismatching chunks: %d", len(mismatches))

    return mismatches


if __name__ == "__main__":
    for i in mismatching_chunks():
        print(i)

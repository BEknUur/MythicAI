from pathlib import Path

async def process_folder(images_dir: Path) -> list[Path]:
    return list(images_dir.glob("*"))

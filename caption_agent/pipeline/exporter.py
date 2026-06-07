"""Pipeline Step 8: Exporter (non-LLM).

Writes a same-basename ``.txt`` sidecar containing the final approved caption for
each ``APPROVED`` image item in the batch.

Per D-087: called during the batch ``Exporting`` state, after all user decisions.
Source images and previously exported sidecars in the folder are NOT deleted or
moved — the exporter only writes / overwrites the ``.txt`` files for accepted items.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ..logging_setup.system_logger import get_system_logger
from ..models import Batch, ImageItem
from ..models.enums import ItemState


def export_batch(batch: Batch, session: Session) -> int:
    """Write .txt sidecars for all APPROVED items in *batch*.

    Returns the count of files written.
    """
    log = get_system_logger()
    items: list[ImageItem] = (
        session.query(ImageItem)
        .filter(
            ImageItem.batch_id == batch.id,
            ImageItem.state == ItemState.APPROVED,
        )
        .all()
    )

    log.debug("[exporter] batch %d — %d APPROVED item(s) to export", batch.id, len(items))

    written = 0
    for item in items:
        if not item.final_caption:
            log.debug("[exporter] item %d — skipped (no final_caption)", item.id)
            continue
        txt_path = _sidecar_path(item)
        txt_path.write_text(item.final_caption + "\n", encoding="utf-8")
        log.debug("[exporter] item %d — wrote %s", item.id, txt_path.name)
        written += 1

    log.debug("[exporter] batch %d — done, %d file(s) written", batch.id, written)
    return written


def _sidecar_path(item: ImageItem) -> Path:
    image_path = Path(item.file_path)
    return image_path.with_suffix(".txt")

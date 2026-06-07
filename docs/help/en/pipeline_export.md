# Export

The final step: writing accepted captions to files next to the images.

## For beginners

After completing review and accepting captions, click the "Export" button in the batch workspace.

Caption Agent will write a text file next to each image, with the same name but the `.txt` extension. If the image is called `portrait_001.jpg`, the caption file will be called `portrait_001.txt`.

These `.txt` files are what the LoRA trainer reads during training.

> **Important:** only images in the APPROVED state are exported. Skipped and dropped images are not exported.

## For professionals

Export writes the `final_caption` field from the image record to the `.txt` file. If `final_caption` is empty, the image is skipped.

Files are written next to the source images — in the same folder that was specified when the batch was created. The exporter does not create subfolders and does not move source files.

Existing `.txt` files are overwritten. This allows re-exporting a batch after review without manual cleanup.

Only APPROVED state is exported. Images in AWAITING_REVIEW, ERROR, or DROPPED states are not exported, even if they have a `normalized_caption`.

After export, the batch transitions to the DONE state.

## Effect on your workflow

File structure after export:

```
images/
  portrait_001.jpg
  portrait_001.txt   ← exported caption
  portrait_002.jpg
  portrait_002.txt
  ...
```

Most LoRA trainers (ai-toolkit, kohya, SimpleTuner) automatically discover `.txt` files next to images. No additional processing is needed.

For review and accepting captions, see [Batch Workspace](ui_batch.md).

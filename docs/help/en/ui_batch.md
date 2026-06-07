# Batch workspace

Where to monitor processing progress and make decisions on captions.

## For beginners

Clicking a batch in the project list opens its workspace. The page has three tabs.

### Overview tab

A summary of the batch: how many images are in each state. While processing is running the counters update automatically. A processing timer with an estimated time remaining is also shown here.

Batch control buttons:

- **Start** — add the batch to the queue.
- **Pause / Resume** — temporarily stop and then continue.
- **Export** — write accepted captions to files.

### Items tab

The full list of images with their current state. For each image you see: a thumbnail, the current state, the normalisation attempt count, and checker warnings. You can expand an image card to read the full caption.

### Review tab

The main working tab after processing completes. It shows images waiting for your decision — one at a time or paginated.

For each image you see:
- The image itself
- The proposed caption
- Checker warnings, if any

Your options:

| Action | When to use |
|---|---|
| **Accept** | Caption is correct and ready for export |
| **Regenerate** | Caption is wrong and needs to be rewritten |
| **Drop** | Image is not needed in the dataset |
| **Skip** | I want to come back to this later |

## For professionals

The Items tab shows all image records regardless of state. Filtering by state lets you quickly find images in ERROR to analyse the failure reason.

Checker warnings are not blockers. They are stored in the image record and are visible during review. You make the final call — accept a caption with a warning or request regeneration.

The Regenerate action returns the image to the normalisation step. The analyst does not re-run. Post-review normalisation attempts are counted separately from the automatic attempts.

Export runs manually or when closing review. It writes accepted captions as `.txt` sidecar files next to the source images — in the same folder that was specified when the batch was created.

## Effect on your workflow

The page updates the batch state and image list automatically while processing is running. No manual refresh needed.

For image state details, see [Image Lifecycle](pipeline_image_lifecycle.md).

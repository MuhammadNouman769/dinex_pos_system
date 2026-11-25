/** Shrink a picture on the phone before upload: max 1000px, JPEG ~82%. Keeps uploads small on weak mobile data. */
export async function compressImage(file: File, max = 1000, quality = 0.82): Promise<File> {
  if (!file.type.startsWith("image/")) throw new Error("Please choose a picture (JPG, PNG or WebP).");
  try {
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const w = Math.round(bmp.width * scale), h = Math.round(bmp.height * scale);
    const canvas = document.createElement("canvas"); canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext("2d"); if (!ctx) return file;
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h); ctx.drawImage(bmp, 0, 0, w, h); bmp.close?.();
    const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", quality));
    if (!blob || blob.size >= file.size) return file.size <= 3 * 1024 * 1024 ? file : (blob ? new File([blob], "photo.jpg", { type: "image/jpeg" }) : file);
    return new File([blob], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch { return file; }
}

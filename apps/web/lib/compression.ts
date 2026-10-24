/**
 * Client-side image compression utility.
 * FR-DIAG-01: Images <= 5 files, each compressed on client to <= 1.5 MB.
 */

export async function compressImage(file: File, maxSizeBytes: number = 1.5 * 1024 * 1024): Promise<File> {
  // If file is already smaller than target, return as-is
  if (file.size <= maxSizeBytes) {
    return file;
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target?.result as string;
      img.onload = () => {
        const canvas = document.createElement("canvas");
        let { width, height } = img;

        // Max resolution threshold for mobile
        const MAX_DIMENSION = 1920;
        if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
          if (width > height) {
            height = Math.round((height * MAX_DIMENSION) / width);
            width = MAX_DIMENSION;
          } else {
            width = Math.round((width * MAX_DIMENSION) / height);
            height = MAX_DIMENSION;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(file);
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);

        // Progressively lower quality until size <= maxSizeBytes
        let quality = 0.85;
        const tryCompress = (q: number) => {
          canvas.toBlob(
            (blob) => {
              if (!blob) {
                resolve(file);
                return;
              }

              if (blob.size <= maxSizeBytes || q <= 0.4) {
                const compressedFile = new File([blob], file.name.replace(/\.[^.]+$/, ".webp"), {
                  type: "image/webp",
                  lastModified: Date.now(),
                });
                resolve(compressedFile);
              } else {
                tryCompress(q - 0.15);
              }
            },
            "image/webp",
            q
          );
        };

        tryCompress(quality);
      };
      img.onerror = () => resolve(file);
    };
    reader.onerror = () => resolve(file);
  });
}

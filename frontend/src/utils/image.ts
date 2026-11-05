// 图片压缩工具：限制宽高、转为 jpeg
function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.readAsDataURL(file)
  })
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('图片解析失败'))
    img.src = src
  })
}

/**
 * 将图片压缩到指定最大宽度并转为 jpeg Blob。
 * 分辨率限制宽 <= maxWidth，压缩质量 quality。
 */
export async function compressImage(
  file: File,
  maxWidth = 1280,
  quality = 0.85,
): Promise<{ blob: Blob; dataUrl: string }> {
  const dataUrl = await readFileAsDataURL(file)
  const img = await loadImage(dataUrl)

  let width = img.width
  let height = img.height
  if (width > maxWidth) {
    const ratio = maxWidth / width
    width = maxWidth
    height = Math.round(height * ratio)
  }

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('浏览器不支持 Canvas')

  ctx.drawImage(img, 0, 0, width, height)
  const preview = canvas.toDataURL('image/jpeg', quality)

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error('图片压缩失败'))),
      'image/jpeg',
      quality,
    )
  })

  return { blob, dataUrl: preview }
}
import { ref } from 'vue'
import { compressImage } from '@/utils/image'
import { uploadImage } from '@/api/modules'
import type { ImageUploadResponse } from '@/types'

export function useImageUpload(imageType: 'tongue' | 'face') {
  const previewUrl = ref('')
  const uploading = ref(false)

  async function uploadFile(sessionId: number, file: File): Promise<ImageUploadResponse> {
    uploading.value = true
    try {
      const { blob, dataUrl } = await compressImage(file)
      previewUrl.value = dataUrl
      return await uploadImage(sessionId, blob, imageType)
    } finally {
      uploading.value = false
    }
  }

  function clear() {
    previewUrl.value = ''
  }

  return { previewUrl, uploading, uploadFile, clear }
}
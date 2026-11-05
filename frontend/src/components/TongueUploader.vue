<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { Camera, Refresh } from '@element-plus/icons-vue'
import { useImageUpload } from '@/composables/useImageUpload'

const props = defineProps<{
  sessionId: number | null
}>()

const emit = defineEmits<{
  (e: 'uploaded', jobId: string, imageId: number): void
  (e: 'error', message: string): void
}>()

const { previewUrl, uploading, uploadFile } = useImageUpload('tongue')

async function handleUpload(options: UploadRequestOptions): Promise<void> {
  if (!props.sessionId) {
    ElMessage.warning('请先创建问诊会话')
    return
  }
  try {
    const resp = await uploadFile(props.sessionId, options.file as File)
    emit('uploaded', resp.job_id, resp.image_id)
  } catch (e) {
    const msg = e instanceof Error ? e.message : '舌象图片上传失败'
    ElMessage.error(msg)
    emit('error', msg)
  }
}

function beforeUpload(file: File): boolean {
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return false
  }
  return true
}
</script>

<template>
  <div class="uploader">
    <div class="uploader-head">
      <span class="uploader-title">舌象</span>
      <span class="uploader-tip">请对准舌面，自然光、避免阴影</span>
    </div>

    <el-upload
      class="uploader-box"
      drag
      :show-file-list="false"
      accept="image/*"
      :http-request="handleUpload"
      :before-upload="beforeUpload"
    >
      <div v-if="previewUrl" class="uploader-preview">
        <img :src="previewUrl" alt="舌象预览" />
        <div class="uploader-mask" v-loading="uploading">
          <el-icon class="mask-icon"><Refresh /></el-icon>
          <span>重新上传</span>
        </div>
      </div>
      <div v-else class="uploader-placeholder" v-loading="uploading">
        <el-icon class="ph-icon"><Camera /></el-icon>
        <div class="ph-title">上传舌象照片</div>
        <div class="ph-sub">支持拍照 / 相册，封面浅色背景更佳</div>
      </div>
    </el-upload>
  </div>
</template>

<style scoped>
.uploader {
  width: 100%;
}

.uploader-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
}

.uploader-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--tcm-text);
}

.uploader-tip {
  font-size: 12px;
  color: var(--tcm-text-faint);
}

.uploader-box :deep(.el-upload),
.uploader-box :deep(.el-upload-dragger) {
  width: 100%;
}

.uploader-box :deep(.el-upload-dragger) {
  background: var(--tcm-bg-soft);
  border-color: var(--tcm-border);
  padding: 20px;
  transition: border-color 0.2s;
}

.uploader-box :deep(.el-upload-dragger:hover) {
  border-color: var(--tcm-primary);
}

.uploader-preview {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
}

.uploader-preview img {
  width: 100%;
  max-height: 260px;
  object-fit: contain;
  display: block;
  background: #08181b;
}

.uploader-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: rgba(8, 24, 27, 0.7);
  color: var(--tcm-text);
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 13px;
}

.uploader-preview:hover .uploader-mask {
  opacity: 1;
}

.mask-icon {
  font-size: 22px;
}

.uploader-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--tcm-text-dim);
}

.ph-icon {
  font-size: 30px;
  color: var(--tcm-primary);
}

.ph-title {
  font-size: 14px;
  color: var(--tcm-text);
}

.ph-sub {
  font-size: 12px;
  color: var(--tcm-text-faint);
}
</style>
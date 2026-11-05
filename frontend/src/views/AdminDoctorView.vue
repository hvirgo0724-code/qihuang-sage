<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { clinical, type Physician } from '@/api/clinical'
import { ElMessage } from 'element-plus'
const doctors = ref<Physician[]>([]), busy = ref(false)
const form = reactive({ username: '', nickname: '', password: '' })
async function load() { try { doctors.value = await clinical.adminDoctors() } catch { ElMessage.error('医生列表加载失败') } }
async function create() { busy.value = true; try { await clinical.createDoctor(form); form.password = ''; form.username = ''; form.nickname = ''; ElMessage.success('医生账号已创建'); await load() } catch { ElMessage.error('创建失败，请检查用户名是否重复、密码是否至少 12 位') } finally { busy.value = false } }
onMounted(load)
</script>
<template><div><div class="page-heading"><div><span class="eyebrow">ACCESS MANAGEMENT</span><h1>医生账号管理</h1><p>管理医生登录账号与访问身份。</p></div><el-button @click="load">刷新列表</el-button></div><section class="workspace-panel"><h2>创建医生账号</h2><p class="tcm-subtitle">请核验医生资质后创建账号，通过安全渠道向医生交付登录信息。</p><el-form label-width="100px" style="max-width: 520px" @submit.prevent="create"><el-form-item label="登录名"><el-input v-model="form.username" maxlength="64" placeholder="字母、数字、下划线、点或横线" /></el-form-item><el-form-item label="医生姓名"><el-input v-model="form.nickname" maxlength="64" /></el-form-item><el-form-item label="初始密码"><el-input v-model="form.password" type="password" show-password autocomplete="new-password" placeholder="至少 12 位，最多 72 字节" /></el-form-item><el-button type="primary" :loading="busy" :disabled="!form.username || !form.nickname || form.password.length < 12" @click="create">创建医生账号</el-button></el-form></section><section class="workspace-panel doctor-directory"><h2>医生目录</h2><el-table :data="doctors"><el-table-column prop="username" label="登录名" /><el-table-column prop="nickname" label="医生姓名" /><el-table-column label="账号状态"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '正常' : row.status === 'disabled' ? '已停用' : row.status }}</el-tag></template></el-table-column></el-table></section></div></template>
<style scoped>h2 { font-size: 17px; margin: 0 0 18px; } .doctor-directory { margin-top: 24px; } .el-form { margin-top: 24px; }</style>

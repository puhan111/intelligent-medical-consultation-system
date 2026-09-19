<template>
  <div class="knowledge-container">
    <div class="toolbar">
      <div class="toolbar-actions">
        <el-button type="primary" :icon="UploadFilled" @click="uploadDialogVisible = true">
          上传知识文档
        </el-button>
        <el-tooltip content="刷新知识库" placement="top">
          <el-button :icon="Refresh" circle :loading="loading" aria-label="刷新知识库" @click="loadKnowledge" />
        </el-tooltip>
      </div>
      <div class="summary">
        <span>已向量化文档 <strong>{{ library.document_count }}</strong></span>
        <el-divider direction="vertical" />
        <span>知识切片 <strong>{{ library.chunk_count }}</strong></span>
      </div>
    </div>

    <el-tabs v-model="activeType" class="knowledge-tabs">
      <el-tab-pane
        v-for="category in library.categories"
        :key="category.source_type"
        :name="category.source_type"
      >
        <template #label>
          <span class="tab-label">
            {{ category.source_type }}
            <el-tag size="small" effect="plain">{{ category.document_count }}</el-tag>
          </span>
        </template>

        <div class="category-meta">
          <span>{{ category.document_count }} 个文档</span>
          <span>{{ category.chunk_count }} 个向量切片</span>
        </div>

        <el-table
          v-loading="loading"
          :data="category.documents"
          row-key="source"
          border
          stripe
          empty-text="暂无已向量化文档"
        >
          <el-table-column prop="source" label="文档来源" min-width="280" show-overflow-tooltip />
          <el-table-column prop="chunk_count" label="切片数" width="120" align="center">
            <template #default="{ row }">
              <el-tag type="success" effect="plain">{{ row.chunk_count }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="130" align="center">
            <template #default>
              <span class="status"><i />向量化完成</span>
            </template>
          </el-table-column>
          <el-table-column label="首次入库" width="190">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="最后更新" width="190">
            <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="uploadDialogVisible" title="上传知识文档" width="600px">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="来源">
          <el-input v-model="uploadForm.source" placeholder="例如：《内科学》第9版" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="uploadForm.source_type" placeholder="请选择类型">
            <el-option label="分诊指引" value="分诊指引" />
            <el-option label="医学参考资料" value="医学参考资料" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容文件">
          <el-upload
            drag
            accept=".md"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :file-list="fileList"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽 .md 文件到此处，或<em>点击选择文件</em></div>
          </el-upload>
          <el-input
            v-if="uploadForm.content"
            v-model="uploadForm.content"
            type="textarea"
            :rows="8"
            class="preview-box"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadFiles } from 'element-plus'
import { getKnowledgeLibrary, uploadKnowledge } from '../../api/knowledge'
import type { KnowledgeLibrary } from '../../types/api'

const SOURCE_TYPES = ['分诊指引', '医学参考资料']
const activeType = ref(SOURCE_TYPES[0])
const loading = ref(false)
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const fileList = ref<UploadFiles>([])
const library = reactive<KnowledgeLibrary>({
  document_count: 0,
  chunk_count: 0,
  categories: SOURCE_TYPES.map((source_type) => ({
    source_type,
    document_count: 0,
    chunk_count: 0,
    documents: [],
  })),
})
const uploadForm = reactive({
  source: '',
  source_type: SOURCE_TYPES[0],
  content: '',
})

function handleFileChange(file: UploadFile) {
  fileList.value = [file]
  if (!file.raw) return
  const reader = new FileReader()
  reader.onload = () => {
    uploadForm.content = (reader.result as string) ?? ''
  }
  reader.readAsText(file.raw, 'utf-8')
}

function handleFileRemove() {
  fileList.value = []
  uploadForm.content = ''
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

async function loadKnowledge() {
  loading.value = true
  try {
    Object.assign(library, await getKnowledgeLibrary())
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  if (!uploadForm.source.trim() || !uploadForm.content.trim()) {
    ElMessage.warning('请填写来源并选择 .md 文件')
    return
  }
  uploading.value = true
  try {
    await uploadKnowledge({ ...uploadForm })
    ElMessage.success('上传成功，正在异步向量化')
    uploadDialogVisible.value = false
    uploadForm.source = ''
    uploadForm.content = ''
    fileList.value = []
    window.setTimeout(loadKnowledge, 2500)
  } finally {
    uploading.value = false
  }
}

onMounted(loadKnowledge)
</script>

<style scoped>
.knowledge-container {
  width: 100%;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.toolbar-actions,
.summary,
.category-meta,
.tab-label,
.status {
  display: flex;
  align-items: center;
}
.toolbar-actions {
  gap: 10px;
}
.summary {
  gap: 6px;
  color: #606266;
  font-size: 14px;
}
.summary strong {
  color: #303133;
}
.knowledge-tabs {
  width: 100%;
}
.tab-label {
  gap: 8px;
}
.category-meta {
  gap: 20px;
  min-height: 38px;
  color: #909399;
  font-size: 13px;
}
.status {
  justify-content: center;
  gap: 7px;
  color: #529b2e;
  font-size: 13px;
}
.status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #67c23a;
}
.preview-box {
  margin-top: 12px;
}
@media (max-width: 760px) {
  .toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .summary {
    width: 100%;
  }
}
</style>

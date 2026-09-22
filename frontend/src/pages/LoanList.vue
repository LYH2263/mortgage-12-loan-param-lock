<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
const items = ref([])
const error = ref('')
const load = async () => { items.value = (await getJSON('/api/loans')).items }
const toggleLock = async (l) => {
  error.value = ''
  try {
    const row = await postJSON(`/api/loans/${l.id}/lock`, { locked: !l.locked })
    l.locked = row.locked
  } catch (e) { error.value = e.message }
}
onMounted(load)
</script>
<template><div class="page"><h1>贷款列表</h1>
<p v-if="error" class="error">{{ error }}</p>
<table><tr><th>名称</th><th>本金</th><th>状态</th><th>操作</th><th></th></tr>
<tr v-for="l in items" :key="l.id">
  <td>{{ l.name }}</td>
  <td>{{ l.principal }}</td>
  <td><span v-if="l.locked" class="badge badge-locked">🔒 已锁定（只读）</span><span v-else class="badge">未锁定</span></td>
  <td><button @click="toggleLock(l)">{{ l.locked ? '解锁' : '锁定' }}</button></td>
  <td><router-link :to="`/loans/${l.id}`">详情</router-link></td>
</tr></table>
</div></template>

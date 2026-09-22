<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
const items = ref([])
const busy = ref(false)
const load = async () => { items.value = (await getJSON('/api/loans')).items }
const toggleLock = async (l) => {
  busy.value = true
  try {
    const next = !l.locked
    await postJSON(`/api/loans/${l.id}/lock`, { locked: next })
    await load()
  } finally { busy.value = false }
}
onMounted(load)
</script>
<template><div class="page"><h1>贷款列表</h1>
<table>
  <tr v-for="l in items" :key="l.id">
    <td>{{ l.name }} <span v-if="l.locked" class="lock-badge">🔒 已锁定</span><span v-else class="unlock-badge">未锁定</span></td>
    <td>{{ l.principal }}</td>
    <td>{{ l.annual_rate }}%</td>
    <td>{{ l.months }} 期</td>
    <td><button :disabled="busy" @click="toggleLock(l)">{{ l.locked ? '解锁' : '锁定' }}</button></td>
    <td><router-link :to="`/loans/${l.id}`">详情</router-link></td>
  </tr>
</table>
</div></template>

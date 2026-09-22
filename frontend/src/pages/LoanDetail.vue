<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, postJSON, patchJSON } from '../api'
const route = useRoute()
const loan = ref(null)
const sch = ref(null)
const form = ref({ principal: 0, annual_rate: 0, months: 0 })
const error = ref('')
const notice = ref('')
const calc = async (persist) => {
  error.value = ''; notice.value = ''
  sch.value = await postJSON('/api/schedule', {
    principal: loan.value.principal, annual_rate: loan.value.annual_rate,
    months: loan.value.months, loan_id: loan.value.id, persist, preview_rows: 6,
  })
  if (persist) notice.value = `测算已写入历史（run_id=${sch.value.run_id}）`
}
const load = async () => {
  loan.value = await getJSON(`/api/loans/${route.params.id}`)
  form.value = { principal: loan.value.principal, annual_rate: loan.value.annual_rate, months: loan.value.months }
  await calc(false)
}
const save = async () => {
  error.value = ''; notice.value = ''
  try {
    loan.value = await patchJSON(`/api/loans/${loan.value.id}`, { ...form.value })
    await calc(false)
    notice.value = '参数已更新，后续测算已使用新参数'
  } catch (e) { error.value = e.message }
}
const toggleLock = async () => {
  error.value = ''; notice.value = ''
  try {
    loan.value = await postJSON(`/api/loans/${loan.value.id}/lock`, { locked: !loan.value.locked })
  } catch (e) { error.value = e.message }
}
onMounted(load); watch(() => route.params.id, load)
</script>
<template><div class="page" v-if="loan"><h1>{{ loan.name }}
  <span v-if="loan.locked" class="badge badge-locked">🔒 已锁定（只读）</span>
  <span v-else class="badge">未锁定</span>
</h1>
<button @click="toggleLock">{{ loan.locked ? '解锁档案' : '锁定档案' }}</button>
<p v-if="sch?.locked" class="hint">本档案处于锁定状态：测算为只读结果，仍可 persist 写入历史。</p>
<p v-if="error" class="error">❌ {{ error }}</p>
<p v-if="notice" class="notice">✅ {{ notice }}</p>
<section class="edit-card">
  <h2>贷款参数</h2>
  <label>本金 <input v-model.number="form.principal" /></label>
  <label>年利率% <input v-model.number="form.annual_rate" /></label>
  <label>月数 <input v-model.number="form.months" /></label>
  <button @click="save">提交修改</button>
  <span v-if="loan.locked" class="hint">（档案已锁定，提交将被拒绝）</span>
</section>
<p>月供 <span class="hero-num">{{ sch?.monthly_payment }}</span></p>
<button @click="calc(true)">保存测算到历史（persist）</button>
<table><tr v-for="r in sch?.preview" :key="r.period"><td>{{ r.period }}</td><td>{{ r.payment }}</td><td>{{ r.principal }}</td><td>{{ r.interest }}</td></tr></table>
</div></template>

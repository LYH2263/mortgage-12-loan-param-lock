<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, postJSON, patchJSON, errMsg } from '../api'
const route = useRoute()
const loan = ref(null)
const sch = ref(null)
const principal = ref(0)
const annual_rate = ref(0)
const months = ref(0)
const errorMsgText = ref('')
const okMsg = ref('')
const busy = ref(false)

const calc = async () => {
  sch.value = await postJSON('/api/schedule', {
    principal: loan.value.principal, annual_rate: loan.value.annual_rate,
    months: loan.value.months, loan_id: loan.value.id, persist: false, preview_rows: 6,
  })
}
const syncForm = () => {
  principal.value = loan.value.principal
  annual_rate.value = loan.value.annual_rate
  months.value = loan.value.months
}
const load = async () => {
  errorMsgText.value = ''
  loan.value = await getJSON(`/api/loans/${route.params.id}`)
  syncForm()
  await calc()
}
const save = async () => {
  errorMsgText.value = ''; okMsg.value = ''; busy.value = true
  try {
    loan.value = await patchJSON(`/api/loans/${loan.value.id}`, {
      principal: Number(principal.value), annual_rate: Number(annual_rate.value), months: Number(months.value),
    })
    syncForm()
    await calc()
    okMsg.value = '参数已更新，后续测算即时生效'
  } catch (e) {
    errorMsgText.value = errMsg(e)
  } finally { busy.value = false }
}
const toggleLock = async () => {
  errorMsgText.value = ''; okMsg.value = ''; busy.value = true
  try {
    loan.value = await postJSON(`/api/loans/${loan.value.id}/lock`, { locked: !loan.value.locked })
    await calc()
  } catch (e) { errorMsgText.value = errMsg(e) } finally { busy.value = false }
}
onMounted(load); watch(() => route.params.id, load)
</script>
<template><div class="page" v-if="loan">
  <h1>{{ loan.name }}
    <span v-if="loan.locked" class="lock-badge">🔒 已锁定</span>
    <span v-else class="unlock-badge">未锁定</span>
  </h1>
  <p v-if="sch && sch.locked === true" class="lock-note">该档案处于锁定状态：参数只读，仍可进行测算。</p>
  <div class="edit-form">
    <label>本金 <input v-model.number="principal" type="number" /></label>
    <label>年利率% <input v-model.number="annual_rate" type="number" step="0.01" /></label>
    <label>期数 <input v-model.number="months" type="number" /></label>
    <button :disabled="busy" @click="save">保存修改</button>
    <button :disabled="busy" class="ghost" @click="toggleLock">{{ loan.locked ? '解锁档案' : '锁定档案' }}</button>
  </div>
  <p v-if="errorMsgText" class="error-box">⚠️ {{ errorMsgText }}</p>
  <p v-if="okMsg" class="ok-box">{{ okMsg }}</p>
  <p>月供 <span class="hero-num">{{ sch?.monthly_payment }}</span>
     <span v-if="sch?.locked" class="lock-tag">locked</span></p>
  <table><tr v-for="r in sch?.preview" :key="r.period"><td>{{ r.period }}</td><td>{{ r.payment }}</td><td>{{ r.principal }}</td><td>{{ r.interest }}</td></tr></table>
</div></template>

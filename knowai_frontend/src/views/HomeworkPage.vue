<template>
  <div class="container"><h1 class="page-title">作业练习</h1><div class="panel"><h3>题目：请说明机器学习中过拟合的原因和解决办法。</h3><el-input v-model="answer" type="textarea" :rows="8" placeholder="输入你的答案" /><div class="actions"><el-button type="primary" @click="submitGrade">AI批改</el-button></div><el-result v-if="grade" icon="success" :title="`${grade.score} 分`" :sub-title="grade.comment" /></div></div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { gradeHomework } from '@/api/ai'
const answer = ref('')
const grade = ref<{ score: number; comment: string }>()
async function submitGrade(){ grade.value = await gradeHomework({ homework_id: 1, student_answer: answer.value }) }
</script>
<style scoped>.actions{margin-top:16px}</style>

<template>
  <div class="pager"><el-pagination background layout="prev, pager, next" :page-size="pageSize" :total="total" :current-page="page" @current-change="$emit('change', $event)" /></div>
</template>

<script setup lang="ts">
defineProps<{ total: number; page: number; pageSize: number }>()
defineEmits<{ change: [page: number] }>()
</script>

<style scoped>
.pager{display:flex;justify-content:center;margin:24px 0}
</style>

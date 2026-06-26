<template><div class="container"><h1 class="page-title">订单详情</h1><div class="panel" v-if="order"><p>订单号：{{ order.order_sn }}</p><p>状态：{{ order.status }}</p><p>金额：￥{{ order.pay_amount }}</p><el-table :data="order.items"><el-table-column prop="course_title" label="课程" /><el-table-column prop="sku_name" label="SKU" /><el-table-column prop="price" label="价格" /></el-table></div></div></template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getOrder, type Order } from '@/api/orders'
const route = useRoute(); const order = ref<Order>()
onMounted(async()=>{ order.value = await getOrder(String(route.params.orderSn)) })
</script>

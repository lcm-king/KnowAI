<template>
  <div class="container"><h1 class="page-title">我的订单</h1>
    <div class="panel">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="未支付" name="unpaid">
          <el-table :data="unpaidOrders" v-loading="loading" stripe empty-text="暂无未支付订单">
            <el-table-column prop="order_sn" label="订单号" min-width="180" />
            <el-table-column prop="pay_amount" label="金额" width="100">
              <template #default="{ row }">¥{{ row.pay_amount }}</template>
            </el-table-column>
            <el-table-column label="下单时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">未支付</template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button v-if="!isExpired(row) && row.status !== 'cancelled'" type="success" size="small" round @click="goPay(row)">去支付</el-button>
                <el-button link size="small" @click="goDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="已支付" name="paid">
          <el-table :data="paidOrders" v-loading="loading" stripe empty-text="暂无已支付订单">
            <el-table-column prop="order_sn" label="订单号" min-width="180" />
            <el-table-column prop="pay_amount" label="金额" width="100">
              <template #default="{ row }">¥{{ row.pay_amount }}</template>
            </el-table-column>
            <el-table-column label="支付时间" width="160">
              <template #default="{ row }">{{ formatTime(row.pay_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button link size="small" @click="goDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listOrders, type Order } from '@/api/orders'

const router = useRouter()
const activeTab = ref('unpaid')
const allOrders = ref<Order[]>([])
const loading = ref(true)

const now = ref(Date.now())

const unpaidOrders = computed(() =>
  allOrders.value.filter((o) => o.status === 'pending' || o.status === 'cancelled')
)
const paidOrders = computed(() =>
  allOrders.value.filter((o) => ['paid', 'learning', 'completed'].includes(o.status))
)

function isExpired(row: Order) {
  return row.status === 'pending' && new Date(row.expire_time).getTime() <= now.value
}

function goPay(row: Order) { router.push(`/pay/${row.order_sn}`) }
function goDetail(row: Order) { router.push(`/orders/${row.order_sn}`) }
function formatTime(t: string) {
  try { return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }
  catch { return t }
}

onMounted(async () => {
  now.value = Date.now()
  try { allOrders.value = (await listOrders({ page: 1, page_size: 50 })).items }
  catch { allOrders.value = [] }
  finally { loading.value = false }
})
</script>

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { addCartItem, getCart, removeCartItem, type CartItem } from '@/api/cart'

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const count = computed(() => items.value.reduce((sum, item) => sum + item.quantity, 0))
  const totalAmount = computed(() => items.value.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0))

  async function refresh() {
    const result = await getCart()
    items.value = result.items
  }

  async function add(skuId: number) {
    await addCartItem(skuId)
    await refresh()
  }

  async function remove(skuId: number) {
    await removeCartItem(skuId)
    await refresh()
  }

  return { items, count, totalAmount, refresh, add, remove }
})

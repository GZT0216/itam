import type { Directive } from 'vue'

import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

type PermissionValue = string | string[]

export const permissionDirective: Directive<HTMLElement, PermissionValue> = {
  mounted(el, binding) {
    const auth = useAuthStore(pinia)
    const codes = Array.isArray(binding.value) ? binding.value : [binding.value]
    if (!auth.hasAnyPerm(codes)) {
      el.remove()
    }
  },
}

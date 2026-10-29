import type { Component } from 'vue'
import {
  Bell,
  Box,
  Connection,
  Cpu,
  DataAnalysis,
  Document,
  Files,
  Finished,
  Grid,
  Key,
  Menu as MenuIcon,
  Monitor,
  Moon,
  OfficeBuilding,
  Odometer,
  Search,
  Setting,
  Sunny,
  Tickets,
  Tools,
  User,
  UserFilled,
} from '@element-plus/icons-vue'

const iconMap: Record<string, Component> = {
  Bell,
  Box,
  Connection,
  Cpu,
  DataAnalysis,
  Document,
  Files,
  Finished,
  Grid,
  Key,
  Menu: MenuIcon,
  Monitor,
  Moon,
  OfficeBuilding,
  Odometer,
  Search,
  Setting,
  Sunny,
  Tickets,
  Tools,
  User,
  UserFilled,
}

export function resolveMenuIcon(name?: string | null): Component {
  return (name && iconMap[name]) || MenuIcon
}

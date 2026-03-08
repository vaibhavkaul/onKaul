export const DEFAULT_DEVICE_IDX = 3 // Desktop (1280×800)

export const DEVICES = [
  { name: '4K',         width: 3840, height: 2160, type: 'desktop' },
  { name: '2K',         width: 2560, height: 1440, type: 'desktop' },
  { name: 'FHD',        width: 1920, height: 1080, type: 'desktop' },
  { name: 'Desktop',    width: 1280, height: 800,  type: 'desktop' },
  { name: 'Laptop',     width: 1024, height: 768,  type: 'desktop' },
  { name: 'iPad',       width: 768,  height: 1024, type: 'tablet'  },
  { name: 'iPhone 15',  width: 393,  height: 852,  type: 'mobile'  },
  { name: 'Pixel 8',    width: 412,  height: 915,  type: 'mobile'  },
  { name: 'Galaxy S24', width: 360,  height: 780,  type: 'mobile'  },
] as const

export type DeviceType = typeof DEVICES[number]['type']

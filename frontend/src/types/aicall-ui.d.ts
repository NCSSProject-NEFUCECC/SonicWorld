declare module 'aicall-ui' {
  interface ARTCAICallUIOptions {
    userId: string
    root: HTMLElement
    shareToken: string
  }

  interface ARTCAICallUI {
    new (options: ARTCAICallUIOptions): ARTCAICallUI
    render(): void
  }

  const ARTCAICallUI: ARTCAICallUI
  export default ARTCAICallUI
}
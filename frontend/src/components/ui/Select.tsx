import * as SelectPrimitive from '@radix-ui/react-select'

export interface SelectOption { value: string; label: string }
export interface SelectProps {
  id: string
  label: string
  value: string
  options: SelectOption[]
  onValueChange: (value: string) => void
  disabled?: boolean
  className?: string
}

export function Select({ id, label, value, options, onValueChange, disabled, className = '' }: SelectProps) {
  return <div className="workspace-select flex flex-col gap-1.5 w-full">
    <label htmlFor={id} className="text-sm font-semibold text-slate-700">{label}</label>
    <SelectPrimitive.Root value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectPrimitive.Trigger id={id} data-value={value} aria-label={label} className={`workspace-select-trigger ${className}`}>
        <SelectPrimitive.Value placeholder={options.find(option => !option.value)?.label} />
        <SelectPrimitive.Icon asChild>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content position="popper" sideOffset={5} collisionPadding={12} className="workspace-select-menu">
          <SelectPrimitive.Viewport>
            {options.filter(option => option.value).map(option => <SelectPrimitive.Item key={option.value} value={option.value} className="workspace-select-option">
              <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
              <SelectPrimitive.ItemIndicator>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>
              </SelectPrimitive.ItemIndicator>
            </SelectPrimitive.Item>)}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  </div>
}

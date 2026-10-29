import React, { useState } from 'react'
import { Modal, Button } from '../ui'

export interface LoginButtonProps {
    fullWidth?: boolean
}

export const LoginButton: React.FC<LoginButtonProps> = ({ fullWidth = false }) => {
    const [isOpen, setIsOpen] = useState(false)

    return (
        <>
            <Button
                variant="nav"
                size="md"
                fullWidth={fullWidth}
                onClick={() => setIsOpen(true)}
                icon={
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
                        />
                    </svg>
                }
            >
                <span>Sign In</span>
            </Button>

            <Modal
                /*TODO: Update this to modal design*/
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                title="Sign In"
                subtitle="Sign in to access your account settings and saved preferences"
                maxWidthClass="max-w-md"
                icon={
                    <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
                        />
                    </svg>
                }
            >
                <div className="space-y-4">
                    <p className="text-sm text-slate-600">
                        Login content goes here.
                    </p>

                    <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                        <Button type="button" variant="ghost" size="sm" onClick={() => setIsOpen(false)}>
                            Cancel
                        </Button>
                        <Button type="button" variant="primary" size="sm" onClick={() => setIsOpen(false)}>
                            Sign In
                        </Button>
                    </div>
                </div>
            </Modal>
        </>
    )
}
'use client'

import { useState, useEffect } from 'react';
import { HiCheckCircle, HiXCircle, HiInformationCircle, HiX } from 'react-icons/hi';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
  type: ToastType;
  message: string;
  duration?: number;
  onClose?: () => void;
}

export default function Toast({ type, message, duration = 5000, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(() => onClose?.(), 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const iconMap = {
    success: <HiCheckCircle className="w-5 h-5 text-green-500" />,
    error: <HiXCircle className="w-5 h-5 text-red-500" />,
    info: <HiInformationCircle className="w-5 h-5 text-blue-500" />
  };

  const bgColorMap = {
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    info: 'bg-blue-50 border-blue-200'
  };

  if (!isVisible) return null;

  return (
    <div className={`fixed top-4 right-4 z-50 transition-all duration-300 ${
      isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
    }`}>
      <div className={`flex items-center gap-3 p-4 rounded-lg border ${bgColorMap[type]} shadow-lg max-w-sm`}>
        {iconMap[type]}
        <p className="text-sm text-gray-700 flex-1">{message}</p>
        <button
          onClick={() => {
            setIsVisible(false);
            setTimeout(() => onClose?.(), 300);
          }}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <HiX className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// Toast container component
export function ToastContainer() {
  const [toasts, setToasts] = useState<Array<{ id: string } & ToastProps>>([]);

  const addToast = (toast: Omit<ToastProps, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { ...toast, id }]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  // Expose to global for use
  if (typeof window !== 'undefined') {
    (window as any).showToast = addToast;
  }

  return (
    <>
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          type={toast.type}
          message={toast.message}
          duration={toast.duration}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </>
  );
}

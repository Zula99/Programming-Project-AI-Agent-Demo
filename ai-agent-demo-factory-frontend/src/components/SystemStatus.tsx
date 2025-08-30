'use client';

import { useState, useEffect } from 'react';
import { FiActivity, FiDatabase, FiGlobe, FiCheckCircle, FiXCircle } from 'react-icons/fi';

interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  url: string;
  responseTime?: number;
}

export default function SystemStatus() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: 'OpenSearch', status: 'running', url: 'http://localhost:9200' },
    { name: 'Backend API', status: 'running', url: 'http://localhost:5000' }
  ]);
  const [loading, setLoading] = useState(true);

  // Check service status
  useEffect(() => {
    const checkServiceStatus = async () => {
      const updatedServices = await Promise.all(
        services.map(async (service) => {
          try {
            const startTime = Date.now();
            const response = await fetch(service.url, { 
              method: 'GET',
              mode: 'no-cors', // Avoid CORS issues
              cache: 'no-cache'
            });
            const responseTime = Date.now() - startTime;
            
            return {
              ...service,
              status: 'running' as const,
              responseTime
            };
          } catch (error) {
            return {
              ...service,
              status: 'error' as const,
              responseTime: undefined
            };
          }
        })
      );
      
      setServices(updatedServices);
      setLoading(false);
    };

    checkServiceStatus();
    
    // Check service status every 60 seconds
    const interval = setInterval(checkServiceStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <FiCheckCircle className="w-5 h-5 text-green-500" />;
      case 'stopped':
        return <FiXCircle className="w-5 h-5 text-gray-400" />;
      case 'error':
        return <FiXCircle className="w-5 h-5 text-red-500" />;
      default:
        return <FiXCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600';
      case 'stopped':
        return 'text-gray-500';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-12 bg-gray-200 rounded"></div>
            <div className="h-12 bg-gray-200 rounded"></div>
            <div className="h-12 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        System Service Status
      </h3>
      
      <div className="space-y-3">
        {services.map((service, index) => (
          <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              {getStatusIcon(service.status)}
              <div>
                <p className="font-medium text-gray-900">{service.name}</p>
                <p className="text-sm text-gray-500">{service.url}</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {service.responseTime && (
                <span className="text-xs text-gray-500">
                  {service.responseTime}ms
                </span>
              )}
              <span className={`text-sm font-medium ${getStatusColor(service.status)}`}>
                {service.status === 'running' ? 'Running' : 
                 service.status === 'stopped' ? 'Stopped' : 'Error'}
              </span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
          <button 
            onClick={() => window.location.reload()}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Refresh Status
          </button>
        </div>
      </div>
    </div>
  );
}

import { useEffect } from 'react';
import axios from 'axios';
import useStore from '../store/useStore';

const useMetricsPoll = () => {
  const { setServerMetrics } = useStore();

  useEffect(() => {
    const poll = async () => {
      try {
        const response = await axios.get('/api/metrics');
        setServerMetrics(response.data);
      } catch (err) {
        console.error('Failed to fetch metrics', err);
      }
    };

    poll();
    const interval = setInterval(poll, 10000);
    return () => clearInterval(interval);
  }, [setServerMetrics]);
};

export default useMetricsPoll;

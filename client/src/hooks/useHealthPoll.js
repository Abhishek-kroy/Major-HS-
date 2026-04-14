import { useEffect } from 'react';
import axios from 'axios';
import useStore from '../store/useStore';

const useHealthPoll = () => {
  const { setFastApiOnline } = useStore();

  useEffect(() => {
    const poll = async () => {
      try {
        const response = await axios.get('/api/health');
        setFastApiOnline(response.data.model_loaded);
      } catch (err) {
        setFastApiOnline(false);
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, [setFastApiOnline]);
};

export default useHealthPoll;

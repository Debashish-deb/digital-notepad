import React, { createContext, useContext, useState } from 'react';

const TaskpadContext = createContext();

export function useTaskpad() {
  return useContext(TaskpadContext);
}

export function TaskpadProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [taskContent, setTaskContent] = useState('');

  const openTaskpad = (content = '') => {
    setTaskContent(content);
    setIsOpen(true);
  };

  const closeTaskpad = () => {
    setIsOpen(false);
    setTaskContent('');
  };

  return (
    <TaskpadContext.Provider value={{ isOpen, taskContent, setTaskContent, openTaskpad, closeTaskpad }}>
      {children}
    </TaskpadContext.Provider>
  );
}

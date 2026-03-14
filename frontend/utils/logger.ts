import pino from 'pino';

const logger = pino({
  browser: {
    asObject: true,
    write: (o: any) => {
      // The correlationId is already in the object from the websocket, so we can just send it.
      // We need to add it for other logs.
      const logPayload = {
        ...o,
        correlationId: o.correlationId || 'not-set',
      };
      
      // Use `fetch` with `keepalive` which is the modern equivalent of `sendBeacon`
      fetch('/api/log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(logPayload),
        keepalive: true,
      }).catch(err => console.error('Failed to send log to backend', err));
    },
  },
  level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
});

export default logger;

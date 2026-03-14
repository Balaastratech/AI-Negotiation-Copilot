import logger from './logger';

export const instrumentedFetch = async (
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> => {
  const correlationId = crypto.randomUUID();

  // Log the outgoing request
  logger.info(
    {
      correlationId,
      url: input.toString(),
      method: init?.method || 'GET',
      body: init?.body,
    },
    'API Request'
  );

  const headers = new Headers(init?.headers);
  headers.set('X-Correlation-ID', correlationId);

  const newInit = { ...init, headers };

  try {
    const response = await fetch(input, newInit);

    // Clone the response to be able to read its body
    const responseToLog = response.clone();
    const responseBody = await responseToLog.json();

    // Log the incoming response
    logger.info(
      {
        correlationId,
        status: response.status,
        statusText: response.statusText,
        body: responseBody,
      },
      'API Response'
    );

    return response;
  } catch (error) {
    logger.error(
      {
        correlationId,
        error,
      },
      'API Request Failed'
    );
    throw error;
  }
};

import { useState, useEffect, useRef, useCallback, useReducer } from 'react';
import { NegotiationWebSocket } from '../lib/websocket';
import { AudioWorkletManager } from '../lib/audio-worklet-manager';
import {
    NegotiationState,
    INITIAL_NEGOTIATION_STATE,
    TranscriptEntry,
    Strategy,
    OutcomeSummary,
    ServerMessageType,
    WebSocketMessage
} from '../lib/types';

type Action =
    | { type: 'SET_CONNECTED'; payload: boolean }
    | { type: 'SET_CONSENTED'; payload: boolean }
    | { type: 'SET_NEGOTIATING'; payload: boolean }
    | { type: 'SET_SESSION_ID'; payload: string }
    | { type: 'APPEND_TRANSCRIPT'; payload: TranscriptEntry }
    | { type: 'SET_STRATEGY'; payload: Strategy }
    | { type: 'SET_OUTCOME'; payload: OutcomeSummary }
    | { type: 'SET_ERROR'; payload: string | null }
    | { type: 'SET_DEGRADED'; payload: boolean }
    | { type: 'SET_AI_STATE'; payload: 'idle' | 'listening' | 'thinking' | 'speaking' };

function negotiationReducer(state: NegotiationState, action: Action): NegotiationState {
    switch (action.type) {
        case 'SET_CONNECTED':
            return { ...state, isConnected: action.payload };
        case 'SET_CONSENTED':
            return { ...state, consentGiven: action.payload };
        case 'SET_NEGOTIATING':
            return { ...state, isNegotiating: action.payload };
        case 'SET_SESSION_ID':
            return { ...state, sessionId: action.payload };
        case 'APPEND_TRANSCRIPT':
            return { ...state, transcript: [...state.transcript, action.payload] };
        case 'SET_STRATEGY':
            return { ...state, strategy: action.payload };
        case 'SET_OUTCOME':
            return { ...state, outcome: action.payload };
        case 'SET_ERROR':
            return { ...state, error: action.payload };
        case 'SET_DEGRADED':
            return { ...state, aiDegraded: action.payload };
        case 'SET_AI_STATE':
            return { ...state, aiState: action.payload };
        default:
            return state;
    }
}

export function useNegotiation() {
    const [state, dispatch] = useReducer(negotiationReducer, INITIAL_NEGOTIATION_STATE);

    const wsRef = useRef<NegotiationWebSocket | null>(null);
    const audioManagerRef = useRef<AudioWorkletManager | null>(null);

    const hasInitialized = useRef(false);

    useEffect(() => {
        if (!hasInitialized.current) {
            audioManagerRef.current = new AudioWorkletManager();
            hasInitialized.current = true;
        }

        return () => {
            // Only disconnect on true unmount not inside strict effect reload
            if (wsRef.current?.isConnected) {
                wsRef.current.disconnect();
            }
        };
    }, []);

    const connect = useCallback(async (wsUrl: string) => {
        if (!audioManagerRef.current) return;

        wsRef.current = new NegotiationWebSocket(wsUrl, audioManagerRef.current);

        wsRef.current.onMessage((msg: WebSocketMessage) => {
            switch (msg.type) {
                case 'CONNECTION_ESTABLISHED':
                    dispatch({ type: 'SET_CONNECTED', payload: true });
                    if ((msg.payload as any)?.session_id) {
                        dispatch({ type: 'SET_SESSION_ID', payload: (msg.payload as any).session_id });
                    }
                    break;
                case 'CONSENT_ACKNOWLEDGED':
                    dispatch({ type: 'SET_CONSENTED', payload: true });
                    break;
                case 'SESSION_STARTED':
                    dispatch({ type: 'SET_NEGOTIATING', payload: true });
                    dispatch({ type: 'SET_AI_STATE', payload: 'listening' });
                    break;
                case 'AI_LISTENING':
                    dispatch({ type: 'SET_AI_STATE', payload: 'listening' });
                    break;
                case 'AI_THINKING':
                    dispatch({ type: 'SET_AI_STATE', payload: 'thinking' });
                    break;
                case 'AI_SPEAKING':
                    dispatch({ type: 'SET_AI_STATE', payload: 'speaking' });
                    break;
                case 'TRANSCRIPT_UPDATE':
                    dispatch({ type: 'APPEND_TRANSCRIPT', payload: msg.payload as TranscriptEntry });
                    // When user speaks, AI is listening
                    const transcriptPayload = msg.payload as TranscriptEntry;
                    if (transcriptPayload.speaker === 'user') {
                        dispatch({ type: 'SET_AI_STATE', payload: 'listening' });
                    }
                    break;
                case 'STRATEGY_UPDATE':
                    dispatch({ type: 'SET_STRATEGY', payload: msg.payload as Strategy });
                    break;
                case 'AI_RESPONSE':
                    const aiPayload = msg.payload as any;
                    dispatch({
                        type: 'APPEND_TRANSCRIPT',
                        payload: {
                            id: `ai_${Date.now()}`,
                            speaker: 'ai',
                            text: aiPayload.text,
                            timestamp: aiPayload.timestamp || Date.now()
                        }
                    });
                    break;
                case 'OUTCOME_SUMMARY':
                    dispatch({ type: 'SET_OUTCOME', payload: msg.payload as OutcomeSummary });
                    dispatch({ type: 'SET_NEGOTIATING', payload: false });
                    dispatch({ type: 'SET_AI_STATE', payload: 'idle' });
                    break;
                case 'AUDIO_INTERRUPTED':
                    if (typeof (audioManagerRef.current as any).clearQueue === 'function') {
                        (audioManagerRef.current as any).clearQueue();
                    }
                    dispatch({ type: 'SET_AI_STATE', payload: 'listening' });
                    break;
                case 'SESSION_RECONNECTING':
                    dispatch({ type: 'SET_ERROR', payload: 'Reconnecting to AI...' });
                    break;
                case 'AI_DEGRADED':
                    dispatch({ type: 'SET_DEGRADED', payload: true });
                    break;
                case 'ERROR':
                    const errPayload = msg.payload as any;
                    dispatch({ type: 'SET_ERROR', payload: errPayload.message || 'Unknown error' });
                    break;
            }
        });

        wsRef.current.onClose(() => {
            dispatch({ type: 'SET_CONNECTED', payload: false });
            dispatch({ type: 'SET_NEGOTIATING', payload: false });
        });

        wsRef.current.onError((err: any) => {
            dispatch({ type: 'SET_ERROR', payload: 'WebSocket connection error' });
        });

        await wsRef.current.connect();
    }, []);

    const grantConsent = useCallback((version: string, mode: string) => {
        wsRef.current?.sendControl('PRIVACY_CONSENT_GRANTED', { version, mode });
    }, []);

    const startNegotiation = useCallback(async (contextStr: string) => {
        await audioManagerRef.current?.initPlayback();

        await audioManagerRef.current?.startCapture(
            (chunk: ArrayBuffer) => {
                wsRef.current?.sendAudioChunk(chunk);
            },
            () => {
                // User stopped speaking - AI is thinking
                dispatch({ type: 'SET_AI_STATE', payload: 'thinking' });
            },
            () => {
                // User started speaking - AI is listening
                dispatch({ type: 'SET_AI_STATE', payload: 'listening' });
            }
        );

        wsRef.current?.sendControl('START_NEGOTIATION', { context: contextStr });
    }, []);

    const endNegotiation = useCallback((finalPrice: number | null, initialPrice: number | null) => {
        wsRef.current?.sendControl('END_NEGOTIATION', { final_price: finalPrice, initial_price: initialPrice });
        audioManagerRef.current?.stopCapture();
    }, []);

    const sendFrame = useCallback((base64Image: string) => {
        wsRef.current?.sendControl('VISION_FRAME', {
            image: base64Image,
            timestamp: Date.now()
        });
    }, []);

    return {
        state,
        connect,
        grantConsent,
        startNegotiation,
        endNegotiation,
        sendFrame
    };
}

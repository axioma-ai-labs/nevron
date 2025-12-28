/**
 * WebSocket store for real-time updates
 */
import { writable, derived, type Readable } from 'svelte/store';
import { browser } from '$app/environment';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketEvent {
	type: string;
	data: Record<string, unknown>;
	timestamp: string;
}

interface WebSocketState {
	status: ConnectionStatus;
	events: WebSocketEvent[];
	lastEvent: WebSocketEvent | null;
	subscribedEvents: string[];
	error: string | null;
}

const MAX_EVENTS = 100;

function createWebSocketStore() {
	let ws: WebSocket | null = null;
	let clientId: string | null = null;
	let reconnectAttempts = 0;
	let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

	const initialState: WebSocketState = {
		status: 'disconnected',
		events: [],
		lastEvent: null,
		subscribedEvents: [],
		error: null
	};

	const { subscribe, set, update } = writable<WebSocketState>(initialState);

	function generateClientId(): string {
		return `dashboard-${Date.now()}-${Math.random().toString(36).substring(7)}`;
	}

	function connect() {
		if (!browser) return;
		if (ws?.readyState === WebSocket.OPEN) return;

		clientId = generateClientId();
		const wsUrl = `ws://${window.location.host}/ws/${clientId}`;

		update((state) => ({ ...state, status: 'connecting', error: null }));

		ws = new WebSocket(wsUrl);

		ws.onopen = () => {
			reconnectAttempts = 0;
			update((state) => ({ ...state, status: 'connected', error: null }));

			// Subscribe to all events
			if (ws) {
				ws.send(JSON.stringify({ action: 'subscribe', events: ['*'] }));
			}
		};

		ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				const wsEvent: WebSocketEvent = {
					type: data.type || 'unknown',
					data: data,
					timestamp: data.timestamp || new Date().toISOString()
				};

				update((state) => ({
					...state,
					events: [wsEvent, ...state.events].slice(0, MAX_EVENTS),
					lastEvent: wsEvent
				}));
			} catch {
				console.error('Failed to parse WebSocket message:', event.data);
			}
		};

		ws.onclose = () => {
			update((state) => ({ ...state, status: 'disconnected' }));
			scheduleReconnect();
		};

		ws.onerror = () => {
			update((state) => ({
				...state,
				status: 'error',
				error: 'WebSocket connection failed'
			}));
		};
	}

	function scheduleReconnect() {
		if (reconnectTimeout) clearTimeout(reconnectTimeout);
		if (reconnectAttempts >= 5) return;

		const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
		reconnectAttempts++;

		reconnectTimeout = setTimeout(() => {
			connect();
		}, delay);
	}

	function disconnect() {
		if (reconnectTimeout) {
			clearTimeout(reconnectTimeout);
			reconnectTimeout = null;
		}
		if (ws) {
			ws.close();
			ws = null;
		}
		set(initialState);
	}

	function subscribeToEvents(events: string[]) {
		if (ws?.readyState === WebSocket.OPEN) {
			ws.send(JSON.stringify({ action: 'subscribe', events }));
			update((state) => ({
				...state,
				subscribedEvents: [...new Set([...state.subscribedEvents, ...events])]
			}));
		}
	}

	function unsubscribeFromEvents(events: string[]) {
		if (ws?.readyState === WebSocket.OPEN) {
			ws.send(JSON.stringify({ action: 'unsubscribe', events }));
			update((state) => ({
				...state,
				subscribedEvents: state.subscribedEvents.filter((e) => !events.includes(e))
			}));
		}
	}

	function clearEvents() {
		update((state) => ({ ...state, events: [], lastEvent: null }));
	}

	function ping() {
		if (ws?.readyState === WebSocket.OPEN) {
			ws.send(JSON.stringify({ action: 'ping' }));
		}
	}

	return {
		subscribe,
		connect,
		disconnect,
		subscribeToEvents,
		unsubscribeFromEvents,
		clearEvents,
		ping
	};
}

export const websocketStore = createWebSocketStore();

// Derived stores for convenience
export const connectionStatus: Readable<ConnectionStatus> = derived(
	websocketStore,
	($ws) => $ws.status
);

export const events: Readable<WebSocketEvent[]> = derived(websocketStore, ($ws) => $ws.events);

export const lastEvent: Readable<WebSocketEvent | null> = derived(
	websocketStore,
	($ws) => $ws.lastEvent
);

import { version } from "../package.json";

interface LogEvent {
	event_type: string;
	outcome: string;
	duration_ms: number;
	[key: string]: unknown;
}

export function logEvent(event: LogEvent): void {
	console.log(JSON.stringify({ timestamp: new Date().toISOString(), version, ...event }));
}

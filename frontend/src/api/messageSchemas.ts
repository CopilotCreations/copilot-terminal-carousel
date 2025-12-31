import { z } from 'zod';

// Session status
export const SessionStatusSchema = z.enum(['running', 'exited']);
export type SessionStatus = z.infer<typeof SessionStatusSchema>;

// Session info from server
export const SessionInfoSchema = z.object({
  sessionId: z.string().uuid(),
  status: SessionStatusSchema,
  createdAt: z.string(),
  lastActivityAt: z.string(),
  workspacePath: z.string(),
  pid: z.number().nullable(),
  cols: z.number(),
  rows: z.number(),
  exitCode: z.number().nullable().optional(),
  copilotPath: z.string().nullable().optional(),
  error: z
    .object({
      code: z.string(),
      message: z.string(),
    })
    .nullable()
    .optional(),
});
export type SessionInfo = z.infer<typeof SessionInfoSchema>;

// Session index entry
export const SessionIndexEntrySchema = z.object({
  sessionId: z.string().uuid(),
  status: SessionStatusSchema,
  createdAt: z.string(),
  lastActivityAt: z.string(),
});
export type SessionIndexEntry = z.infer<typeof SessionIndexEntrySchema>;

// Server -> Client messages
export const ServerHelloMessageSchema = z.object({
  type: z.literal('server.hello'),
  serverTime: z.string(),
  protocolVersion: z.number(),
});

export const SessionCreatedMessageSchema = z.object({
  type: z.literal('session.created'),
  session: SessionInfoSchema,
});

export const SessionAttachedMessageSchema = z.object({
  type: z.literal('session.attached'),
  sessionId: z.string().uuid(),
  status: SessionStatusSchema,
});

export const SessionListResultMessageSchema = z.object({
  type: z.literal('session.list.result'),
  sessions: z.array(SessionIndexEntrySchema),
});

export const SessionExitedMessageSchema = z.object({
  type: z.literal('session.exited'),
  sessionId: z.string().uuid(),
  exitCode: z.number().nullable(),
});

export const TerminalOutputMessageSchema = z.object({
  type: z.literal('term.out'),
  sessionId: z.string().uuid(),
  data: z.string(),
});

export const ErrorMessageSchema = z.object({
  type: z.literal('error'),
  code: z.string(),
  message: z.string(),
});

// Union of all server messages
export const ServerMessageSchema = z.discriminatedUnion('type', [
  ServerHelloMessageSchema,
  SessionCreatedMessageSchema,
  SessionAttachedMessageSchema,
  SessionListResultMessageSchema,
  SessionExitedMessageSchema,
  TerminalOutputMessageSchema,
  ErrorMessageSchema,
]);
export type ServerMessage = z.infer<typeof ServerMessageSchema>;

// Client -> Server messages
export interface SessionCreateMessage {
  type: 'session.create';
}

export interface SessionAttachMessage {
  type: 'session.attach';
  sessionId: string;
}

export interface SessionListMessage {
  type: 'session.list';
}

export interface SessionTerminateMessage {
  type: 'session.terminate';
  sessionId: string;
}

export interface TerminalInputMessage {
  type: 'term.in';
  sessionId: string;
  data: string;
}

export interface TerminalResizeMessage {
  type: 'term.resize';
  sessionId: string;
  cols: number;
  rows: number;
}

export type ClientMessage =
  | SessionCreateMessage
  | SessionAttachMessage
  | SessionListMessage
  | SessionTerminateMessage
  | TerminalInputMessage
  | TerminalResizeMessage;

// Parse and validate a server message
export function parseServerMessage(data: unknown): ServerMessage | null {
  try {
    return ServerMessageSchema.parse(data);
  } catch {
    console.error('Failed to parse server message:', data);
    return null;
  }
}

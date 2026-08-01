import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Play, CheckCircle, XCircle, Clock, ChevronRight, Loader } from 'lucide-react';
import { TOOL_SCHEMAS, TOOL_MAP, CATEGORY_LABELS } from '../data/tools';
import type { ToolSchema } from '../data/tools';
import { PageHeader, Card } from '../components/PageHeader';
import { cn } from '../lib/utils';

// ─── Run history entry ────────────────────────────────────────────

interface RunEntry {
  id: string;
  toolName: string;
  inputs: Record<string, string>;
  output: unknown;
  status: 'success' | 'error';
  durationMs: number;
  ranAt: string;
}

// ─── Input field renderer ─────────────────────────────────────────

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: import('../data/tools').ToolField;
  value: string;
  onChange: (v: string) => void;
}) {
  const base: React.CSSProperties = {
    background: 'var(--bg)',
    border: '1px solid var(--border-md)',
    borderRadius: 8,
    color: 'var(--text-primary)',
    fontSize: 13,
    width: '100%',
    outline: 'none',
    transition: 'border-color 0.15s',
  };

  const onFocus = (e: React.FocusEvent<HTMLElement>) =>
    ((e.currentTarget as HTMLElement).style.borderColor = 'var(--accent-border)');
  const onBlur = (e: React.FocusEvent<HTMLElement>) =>
    ((e.currentTarget as HTMLElement).style.borderColor = 'var(--border-md)');

  if (field.type === 'select') {
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={onFocus}
        onBlur={onBlur}
        style={{ ...base, padding: '8px 12px' }}
      >
        {field.options?.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    );
  }

  if (field.type === 'textarea') {
    return (
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={onFocus}
        onBlur={onBlur}
        placeholder={field.placeholder}
        rows={4}
        style={{ ...base, padding: '8px 12px', resize: 'vertical', fontFamily: 'inherit' }}
      />
    );
  }

  return (
    <input
      type={field.type === 'number' ? 'number' : 'text'}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={onFocus}
      onBlur={onBlur}
      placeholder={field.placeholder}
      style={{ ...base, padding: '8px 12px' }}
    />
  );
}

// ─── Output viewer ────────────────────────────────────────────────

function OutputPanel({ run }: { run: RunEntry }) {
  const json = JSON.stringify(run.output, null, 2);

  return (
    <div className="flex flex-col gap-3">
      {/* Status bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          {run.status === 'success'
            ? <CheckCircle size={14} style={{ color: 'var(--success)' }} />
            : <XCircle size={14} style={{ color: 'var(--danger)' }} />}
          <span className="text-[13px] font-medium" style={{ color: run.status === 'success' ? 'var(--success)' : 'var(--danger)' }}>
            {run.status === 'success' ? 'Success' : 'Error'}
          </span>
        </div>
        <div className="flex items-center gap-1.5" style={{ color: 'var(--text-tertiary)' }}>
          <Clock size={12} />
          <span className="text-[12px]">{run.durationMs}ms</span>
        </div>
        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{run.ranAt}</span>
      </div>

      {/* JSON output */}
      <div
        className="rounded-xl overflow-auto"
        style={{
          background: 'var(--bg)',
          border: '1px solid var(--border)',
          maxHeight: 360,
        }}
      >
        <pre
          className="p-4 text-[12px] leading-relaxed m-0"
          style={{ color: 'var(--text-secondary)', fontFamily: 'ui-monospace, monospace' }}
        >
          {json}
        </pre>
      </div>
    </div>
  );
}

// ─── History item ─────────────────────────────────────────────────

function HistoryItem({ run, active, onClick }: { run: RunEntry; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 rounded-lg transition-all flex items-center gap-2.5"
      style={{
        background: active ? 'var(--accent-dim)' : 'transparent',
        border: `1px solid ${active ? 'var(--accent-border)' : 'transparent'}`,
      }}
    >
      {run.status === 'success'
        ? <CheckCircle size={12} style={{ color: 'var(--success)', flexShrink: 0 }} />
        : <XCircle size={12} style={{ color: 'var(--danger)', flexShrink: 0 }} />}
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-medium truncate" style={{ color: active ? 'var(--accent-light)' : 'var(--text-secondary)' }}>
          {run.toolName}
        </p>
        <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{run.durationMs}ms · {run.ranAt}</p>
      </div>
    </button>
  );
}

// ─── Page ─────────────────────────────────────────────────────────

export function ToolsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const preselect = searchParams.get('tool');

  const [selectedTool, setSelectedTool] = useState<ToolSchema>(
    (preselect && TOOL_MAP[preselect]) ? TOOL_MAP[preselect] : TOOL_SCHEMAS[0]
  );
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState<RunEntry[]>([]);
  const [activeRun, setActiveRun] = useState<RunEntry | null>(null);

  // When tool changes, reset inputs to defaults
  useEffect(() => {
    const defaults: Record<string, string> = {};
    for (const f of selectedTool.fields) {
      defaults[f.key] = f.defaultValue !== undefined ? String(f.defaultValue) : '';
    }
    setInputs(defaults);
  }, [selectedTool]);

  // Sync URL param when tool changes
  const selectTool = (tool: ToolSchema) => {
    setSelectedTool(tool);
    setSearchParams({ tool: tool.name });
    setActiveRun(null);
  };

  const handleRun = async () => {
    // Validate required fields
    for (const f of selectedTool.fields) {
      if (f.required && !inputs[f.key]?.trim()) return;
    }

    setRunning(true);
    setActiveRun(null);

    // Simulate network latency
    const start = Date.now();
    await new Promise((r) => setTimeout(r, 400 + Math.random() * 400));
    const durationMs = Date.now() - start;

    const output = selectedTool.mockOutput(inputs);
    const entry: RunEntry = {
      id: crypto.randomUUID(),
      toolName: selectedTool.name,
      inputs: { ...inputs },
      output,
      status: 'success',
      durationMs,
      ranAt: new Date().toLocaleTimeString('en-US', { hour12: false }),
    };

    setRunning(false);
    setHistory((prev) => [entry, ...prev.slice(0, 19)]);
    setActiveRun(entry);
  };

  // Group tools by category
  const grouped = TOOL_SCHEMAS.reduce<Record<string, ToolSchema[]>>((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});

  const canRun = !running && selectedTool.fields
    .filter((f) => f.required)
    .every((f) => inputs[f.key]?.trim());

  return (
    <div className="px-8 py-8 max-w-[1400px]">
      <PageHeader
        title="Tools"
        description="Select a tool, fill in inputs, and run it directly"
      />

      <div className="grid grid-cols-12 gap-5" style={{ minHeight: 600 }}>

        {/* ── Left: tool selector ── */}
        <div className="col-span-3">
          <Card className="overflow-hidden">
            <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
              <p className="text-[11px] font-semibold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
                Available Tools
              </p>
            </div>
            <div className="p-2">
              {Object.entries(grouped).map(([cat, tools]) => (
                <div key={cat} className="mb-3">
                  <p className="px-2 py-1 text-[10px] font-semibold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
                    {CATEGORY_LABELS[cat] ?? cat}
                  </p>
                  {tools.map((tool) => {
                    const active = selectedTool.name === tool.name;
                    return (
                      <button
                        key={tool.name}
                        onClick={() => selectTool(tool)}
                        className="w-full text-left px-3 py-2.5 rounded-lg transition-all flex items-center justify-between group"
                        style={{
                          background: active ? 'var(--accent-dim)' : 'transparent',
                          border: `1px solid ${active ? 'var(--accent-border)' : 'transparent'}`,
                          marginBottom: 2,
                        }}
                      >
                        <div>
                          <p className="text-[13px] font-medium" style={{ color: active ? 'var(--accent-light)' : 'var(--text-secondary)' }}>
                            {tool.label}
                          </p>
                          <code className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{tool.name}</code>
                        </div>
                        {active && <ChevronRight size={12} style={{ color: 'var(--accent-light)', flexShrink: 0 }} />}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </Card>

          {/* Run history */}
          {history.length > 0 && (
            <Card className="mt-4 overflow-hidden">
              <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
                <p className="text-[11px] font-semibold tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
                  Run History
                </p>
              </div>
              <div className="p-2 space-y-0.5">
                {history.map((r) => (
                  <HistoryItem
                    key={r.id}
                    run={r}
                    active={activeRun?.id === r.id}
                    onClick={() => {
                      setActiveRun(r);
                      if (TOOL_MAP[r.toolName]) selectTool(TOOL_MAP[r.toolName]);
                    }}
                  />
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* ── Right: form + output ── */}
        <div className="col-span-9 flex flex-col gap-5">

          {/* Tool header */}
          <Card className="px-6 py-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h2 className="text-[17px] font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {selectedTool.label}
                  </h2>
                  <code
                    className="text-[11px] px-2 py-0.5 rounded"
                    style={{ background: 'var(--bg-3)', color: 'var(--text-tertiary)' }}
                  >
                    {selectedTool.name}
                  </code>
                </div>
                <p className="text-[13px]" style={{ color: 'var(--text-tertiary)' }}>
                  {selectedTool.description}
                </p>
              </div>
              <button
                onClick={handleRun}
                disabled={!canRun}
                className={cn(
                  'flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-semibold transition-all flex-shrink-0',
                  canRun ? 'cursor-pointer' : 'cursor-not-allowed opacity-40'
                )}
                style={{
                  background: canRun ? 'var(--accent)' : 'var(--bg-3)',
                  color: canRun ? '#ffffff' : 'var(--text-muted)',
                  boxShadow: canRun ? '0 2px 12px rgba(124,106,247,0.35)' : 'none',
                }}
              >
                {running
                  ? <Loader size={14} className="animate-spin" />
                  : <Play size={14} strokeWidth={2.5} />}
                {running ? 'Running…' : 'Run Tool'}
              </button>
            </div>
          </Card>

          {/* Input form */}
          <Card className="px-6 py-5">
            <p className="text-[11px] font-semibold tracking-widest uppercase mb-5" style={{ color: 'var(--text-muted)' }}>
              Inputs
            </p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-5">
              {selectedTool.fields.map((field) => (
                <div
                  key={field.key}
                  className={cn(field.type === 'textarea' && 'col-span-2')}
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <label className="text-[12px] font-medium" style={{ color: 'var(--text-secondary)' }}>
                      {field.label}
                    </label>
                    {field.required && (
                      <span className="text-[10px]" style={{ color: 'var(--accent)' }}>*</span>
                    )}
                  </div>
                  {field.description && (
                    <p className="text-[11px] mb-1.5" style={{ color: 'var(--text-muted)' }}>
                      {field.description}
                    </p>
                  )}
                  <FieldInput
                    field={field}
                    value={inputs[field.key] ?? ''}
                    onChange={(v) => setInputs((prev) => ({ ...prev, [field.key]: v }))}
                  />
                </div>
              ))}
            </div>
          </Card>

          {/* Output */}
          {(running || activeRun) && (
            <Card className="px-6 py-5">
              <p className="text-[11px] font-semibold tracking-widest uppercase mb-4" style={{ color: 'var(--text-muted)' }}>
                Output
              </p>
              {running ? (
                <div className="flex items-center gap-3 py-8 justify-center">
                  <Loader size={16} className="animate-spin" style={{ color: 'var(--accent)' }} />
                  <span className="text-[13px]" style={{ color: 'var(--text-tertiary)' }}>
                    Executing {selectedTool.name}…
                  </span>
                </div>
              ) : activeRun ? (
                <OutputPanel run={activeRun} />
              ) : null}
            </Card>
          )}

          {/* Empty state */}
          {!running && !activeRun && (
            <Card className="flex flex-col items-center justify-center py-16 gap-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'var(--bg-3)' }}
              >
                <Play size={16} style={{ color: 'var(--text-muted)' }} />
              </div>
              <p className="text-[13px] font-medium" style={{ color: 'var(--text-tertiary)' }}>
                Fill in the inputs and click Run Tool
              </p>
              <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
                Output will appear here
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

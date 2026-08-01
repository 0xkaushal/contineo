// ─── Tool field types ─────────────────────────────────────────────

export type FieldType = 'text' | 'number' | 'select' | 'textarea';

export interface ToolField {
  key: string;
  label: string;
  type: FieldType;
  placeholder?: string;
  required?: boolean;
  options?: string[];            // for select
  defaultValue?: string | number;
  description?: string;
}

export interface ToolSchema {
  name: string;
  label: string;
  description: string;
  category: 'weather' | 'search' | 'file' | 'format' | 'data';
  fields: ToolField[];
  mockOutput: (inputs: Record<string, string>) => unknown;
}

// ─── Tool definitions ─────────────────────────────────────────────

export const TOOL_SCHEMAS: ToolSchema[] = [
  {
    name: 'get_weather',
    label: 'Get Weather',
    description: 'Fetch current weather conditions for a city.',
    category: 'weather',
    fields: [
      {
        key: 'city',
        label: 'City',
        type: 'text',
        placeholder: 'e.g. San Francisco',
        required: true,
      },
      {
        key: 'units',
        label: 'Units',
        type: 'select',
        options: ['metric', 'imperial', 'kelvin'],
        defaultValue: 'metric',
      },
    ],
    mockOutput: (inputs) => ({
      city: inputs.city || 'San Francisco',
      temperature: 20,
      feels_like: 18,
      condition: 'Partly Cloudy',
      humidity: 72,
      wind_speed: 14,
      wind_direction: 'NW',
      units: inputs.units || 'metric',
      retrieved_at: new Date().toISOString(),
    }),
  },

  {
    name: 'get_forecast',
    label: 'Get Forecast',
    description: 'Fetch a multi-day weather forecast for a city.',
    category: 'weather',
    fields: [
      {
        key: 'city',
        label: 'City',
        type: 'text',
        placeholder: 'e.g. New York',
        required: true,
      },
      {
        key: 'days',
        label: 'Days',
        type: 'number',
        placeholder: '3',
        defaultValue: 3,
        description: 'Number of forecast days (1–7)',
      },
      {
        key: 'units',
        label: 'Units',
        type: 'select',
        options: ['metric', 'imperial'],
        defaultValue: 'metric',
      },
    ],
    mockOutput: (inputs) => {
      const days = Math.min(7, Math.max(1, parseInt(inputs.days || '3')));
      return {
        city: inputs.city || 'New York',
        units: inputs.units || 'metric',
        forecast: Array.from({ length: days }, (_, i) => ({
          date: new Date(Date.now() + (i + 1) * 86400000).toISOString().slice(0, 10),
          high: 22 - i,
          low: 14 - i,
          condition: ['Sunny', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Sunny'][i % 5],
          precipitation_chance: [10, 20, 40, 70, 15][i % 5],
        })),
      };
    },
  },

  {
    name: 'search_web',
    label: 'Search Web',
    description: 'Run a web search and return top results.',
    category: 'search',
    fields: [
      {
        key: 'query',
        label: 'Query',
        type: 'text',
        placeholder: 'e.g. latest AI research papers',
        required: true,
      },
      {
        key: 'num_results',
        label: 'Results',
        type: 'number',
        placeholder: '5',
        defaultValue: 5,
        description: 'Max results to return (1–10)',
      },
    ],
    mockOutput: (inputs) => {
      const n = Math.min(10, Math.max(1, parseInt(inputs.num_results || '5')));
      return {
        query: inputs.query || '',
        results: Array.from({ length: n }, (_, i) => ({
          rank: i + 1,
          title: `Result ${i + 1} for "${inputs.query || 'query'}"`,
          url: `https://example.com/result-${i + 1}`,
          snippet: `This is a snippet for result ${i + 1}. It contains relevant information about the search query.`,
          published: new Date(Date.now() - i * 86400000 * 3).toISOString().slice(0, 10),
        })),
        total_results: 1_420_000,
        search_time_ms: 142,
      };
    },
  },

  {
    name: 'read_file',
    label: 'Read File',
    description: 'Read the contents of a file by path.',
    category: 'file',
    fields: [
      {
        key: 'path',
        label: 'File Path',
        type: 'text',
        placeholder: 'e.g. /data/report.txt',
        required: true,
      },
      {
        key: 'encoding',
        label: 'Encoding',
        type: 'select',
        options: ['utf-8', 'ascii', 'base64'],
        defaultValue: 'utf-8',
      },
    ],
    mockOutput: (inputs) => ({
      path: inputs.path || '/data/report.txt',
      encoding: inputs.encoding || 'utf-8',
      size_bytes: 2048,
      content: `# Report\n\nThis is the content of ${inputs.path || '/data/report.txt'}.\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.`,
      last_modified: new Date(Date.now() - 86400000 * 2).toISOString(),
    }),
  },

  {
    name: 'write_file',
    label: 'Write File',
    description: 'Write content to a file at the specified path.',
    category: 'file',
    fields: [
      {
        key: 'path',
        label: 'File Path',
        type: 'text',
        placeholder: 'e.g. /output/result.txt',
        required: true,
      },
      {
        key: 'content',
        label: 'Content',
        type: 'textarea',
        placeholder: 'File contents...',
        required: true,
      },
      {
        key: 'mode',
        label: 'Write Mode',
        type: 'select',
        options: ['overwrite', 'append', 'create_new'],
        defaultValue: 'overwrite',
      },
    ],
    mockOutput: (inputs) => ({
      path: inputs.path || '/output/result.txt',
      mode: inputs.mode || 'overwrite',
      bytes_written: (inputs.content || '').length,
      success: true,
      written_at: new Date().toISOString(),
    }),
  },

  {
    name: 'format_response',
    label: 'Format Response',
    description: 'Format raw data into a clean human-readable response.',
    category: 'format',
    fields: [
      {
        key: 'data',
        label: 'Input Data',
        type: 'textarea',
        placeholder: 'Raw data to format...',
        required: true,
      },
      {
        key: 'format',
        label: 'Output Format',
        type: 'select',
        options: ['markdown', 'plain', 'html', 'json'],
        defaultValue: 'markdown',
      },
      {
        key: 'tone',
        label: 'Tone',
        type: 'select',
        options: ['professional', 'casual', 'concise'],
        defaultValue: 'professional',
      },
    ],
    mockOutput: (inputs) => ({
      format: inputs.format || 'markdown',
      tone: inputs.tone || 'professional',
      original_length: (inputs.data || '').length,
      formatted: `## Summary\n\n${inputs.data || 'No input provided.'}\n\n*Formatted in ${inputs.format || 'markdown'} with ${inputs.tone || 'professional'} tone.*`,
      processing_ms: 38,
    }),
  },
];

export const TOOL_MAP = Object.fromEntries(TOOL_SCHEMAS.map((t) => [t.name, t]));

export const CATEGORY_LABELS: Record<string, string> = {
  weather: 'Weather',
  search:  'Search',
  file:    'File System',
  format:  'Formatting',
  data:    'Data',
};

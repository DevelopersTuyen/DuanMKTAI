export const environment = {
  production: true,
  apiBaseUrl: 'http://localhost:8000/api',
  ollama: {
    baseUrl: 'http://localhost:11434',
    model: 'qwen3:8b',
  },
  googleSheets: {
    spreadsheetId: 'your-google-sheet-id',
    worksheet: 'social_overview',
  },
  sync: {
    intervalMinutes: 60,
  },
};

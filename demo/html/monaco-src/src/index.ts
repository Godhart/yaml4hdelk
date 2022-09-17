import './index.css';

// NOTE: Schemas selector is disabled so this one isn't required
import { JSONSchemaForSchemaStoreOrgCatalogFiles } from '@schemastore/schema-catalog';
import { ILanguageFeaturesService } from 'monaco-editor/esm/vs/editor/common/services/languageFeatures.js';
import { OutlineModel } from 'monaco-editor/esm/vs/editor/contrib/documentSymbols/browser/outlineModel.js';
import {
  editor,
  Environment,
  languages,
  MarkerSeverity,
  Position,
  Range,
  Uri,
} from 'monaco-editor/esm/vs/editor/editor.api.js';
import { StandaloneServices } from 'monaco-editor/esm/vs/editor/standalone/browser/standaloneServices.js';
import { SchemasSettings, setDiagnosticsOptions } from 'monaco-yaml';

// NOTE: This will give you all editor features. If you would prefer to limit to only the editor
// features you want to use, import them each individually. See this example: (https://github.com/microsoft/monaco-editor-samples/blob/main/browser-esm-webpack-small/index.js#L1-L91)
import 'monaco-editor';

import defaultSchemaUri from './schema.json';

declare global {
  interface Window {
    MonacoEnvironment: Environment;
  }
}

window.MonacoEnvironment = {
  getWorker(moduleId, label) {
    switch (label) {
      case 'editorWorkerService':
        return new Worker(new URL('monaco-editor/esm/vs/editor/editor.worker', import.meta.url));
      case 'yaml':
        return new Worker(new URL('monaco-yaml/yaml.worker', import.meta.url));
      default:
        throw new Error(`Unknown label ${label}`);
    }
  },
};

const defaultSchema: SchemasSettings = {
  uri: defaultSchemaUri,
  fileMatch: ['schm.yaml'],
};

setDiagnosticsOptions({
  schemas: [defaultSchema],
});

const ed = editor.create(document.getElementById('editor'), {
  automaticLayout: true,
  model: null,
  theme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'vs-dark' : 'vs-light',
});

class Context {
  model: editor.ITextModel;
  state: editor.ICodeEditorViewState;

  constructor(value: string) {
    this.model = editor.createModel(value, 'yaml', Uri.parse('schm.yaml'));
    this.state = null;
  }
}

function noop(): null {
  return null;
}

class Contexts {
  contexts: Record<string, Context>;
  current: string;
  editor: editor.IStandaloneCodeEditor;
  zeroView : editor.ICodeEditorViewState;

  constructor(editor: editor.IStandaloneCodeEditor) {
    this.contexts = {};
    this.current = '';
    this.zeroView = null;
    this.editor = editor;
  }

  contextAdd(contextName: string, value: string): number {
    console.log('contextAdd: ' + contextName);
    if (contextName === '') {
      return -2;
    }
    if (this.contexts[contextName] !== undefined) {
      return -1;
    }

    this.contexts[contextName] = new Context(value);
    return 0;
  }

  contextRemove(contextName: string): number {
    if (contextName === '') {
      return -2;
    }
    if (this.contexts[contextName] === undefined) {
      return -1;
    }

    delete this.contexts[contextName];
    return 0;
  }

  contextSwitch(contextName: string): number {
    console.log('contextSwitch: ' + contextName);
    if (this.contexts[contextName] === undefined) {
      return -1;
    }
    if (contextName === this.current) {
      return 0;
    }
    if (this.current !== '') {
      this.contexts[this.current].state = ed.saveViewState();
    } else {
        if (this.zeroView == null) {
            this.zeroView = ed.saveViewState();
        }
    }
    if (contextName === '') {
      this.current = '';
      ed.setModel(this.contexts[this.current].model);
      if (this.zeroView != null) {
        ed.restoreViewState(this.zeroView);
      }
      ed.focus();
    } else {
      this.current = contextName;
      ed.setModel(this.contexts[this.current].model);
      ed.restoreViewState(this.contexts[this.current].state);
      ed.focus();
    }
    return 0;
  }

  contextCurrent(): string {
    return this.current;
  }

  contextValueGet(contextName: string): string {
    if (contextName === '') {
      return null;
    }
    if (this.contexts[contextName] === undefined) {
      return null;
    }
    return this.contexts[contextName].model.getValue();
  }

  contextValueSet(contextName: string, value: string): number {
    if (contextName === '') {
      return -2;
    }
    if (this.contexts[contextName] === undefined) {
      return -1;
    }
    this.contexts[contextName].model.setValue(value);
    return 0;
  }

  contextList(): string[] {
    const result: string[] = [];
    for (const [key, value] of Object.entries(this.contexts)) {
      result.push(key);
      if (value == null) {
        noop();
      }
    }
    return result;
  }

  contextDump(): Record<string, string> {
    const result: Record<string, string> = {};
    for (const [key, value] of Object.entries(this.contexts)) {
      result[key] = value.model.getValue();
    }
    return result;
  }
}

const contexts = new Contexts(ed);

document.worker = contexts;

// NOTE: disabled - const select = document.getElementById('schema-selection') as HTMLSelectElement;

const schemas = [defaultSchema];

/* NOTE: external schemas are disabled
fetch('https://www.schemastore.org/api/json/catalog.json').then(async (response) => {
  if (!response.ok) {
    return;
  }
  const catalog = (await response.json()) as JSONSchemaForSchemaStoreOrgCatalogFiles;
  catalog.schemas.sort((a, b) => a.name.localeCompare(b.name));
  for (const { fileMatch, name, url } of catalog.schemas) {
    const match =
      typeof name === 'string' && fileMatch?.find((filename) => /\.ya?ml$/i.test(filename));
    if (!match) {
      continue;
    }
    const option = document.createElement('option');
    option.value = match;

    option.textContent = name;
    select.append(option);
    schemas.push({
      fileMatch: [match],
      uri: url,
    });
  }
});
*/

setDiagnosticsOptions({
  validate: true,
  enableSchemaRequest: true,
  format: true,
  hover: true,
  completion: true,
  schemas,
});

/* NOTE: disabled SCHEMA selection

select.addEventListener('change', () => {
  const oldModel = ed.getModel();
  const newModel = editor.createModel(oldModel.getValue(), 'yaml', Uri.parse(select.value));
  ed.setModel(newModel);
  oldModel.dispose();
});

*/

function* iterateSymbols(
  symbols: languages.DocumentSymbol[],
  position: Position,
): Iterable<languages.DocumentSymbol> {
  for (const symbol of symbols) {
    if (Range.containsPosition(symbol.range, position)) {
      yield symbol;
      if (symbol.children) {
        yield* iterateSymbols(symbol.children, position);
      }
    }
  }
}

class Settings {
  onChangeListener: string;
  hostDomain: string;

  constructor() {
    this.onChangeListener = null;
    this.hostDomain = '*';
  }

  onChangeListenerSet(value: string): void {
    this.onChangeListener = value;
  }

  hostDomainSet(value: string): void {
    this.hostDomain = value;
  }
}

const settings = new Settings();

document.settings = settings;

ed.onDidChangeModelContent((event) => {
  if (settings.onChangeListener != null) {
    if (window.parent === undefined || window.parent == null) {
      return null;
    }
    window.parent.postMessage(
      {
        func: 'call',
        obj: settings.onChangeListener,
        method: 'onEditorChange',
        args: [contexts.contextCurrent()],
        callback: undefined,
      },
      settings.hostDomain,
    );
  }
});

ed.onDidChangeCursorPosition(async (event) => {
  const breadcrumbs = document.getElementById('breadcrumbs');
  const { documentSymbolProvider } = StandaloneServices.get(ILanguageFeaturesService);
  const outline = await OutlineModel.create(documentSymbolProvider, ed.getModel());
  const symbols = outline.asListOfDocumentSymbols();
  while (breadcrumbs.lastChild) {
    breadcrumbs.lastChild.remove();
  }
  for (const symbol of iterateSymbols(symbols, event.position)) {
    const breadcrumb = document.createElement('span');
    breadcrumb.setAttribute('role', 'button');
    breadcrumb.classList.add('breadcrumb');
    breadcrumb.textContent = symbol.name;
    breadcrumb.title = symbol.detail;
    if (symbol.kind === languages.SymbolKind.Array) {
      breadcrumb.classList.add('array');
    } else if (symbol.kind === languages.SymbolKind.Module) {
      breadcrumb.classList.add('object');
    }
    breadcrumb.addEventListener('click', () => {
      ed.setPosition({
        lineNumber: symbol.range.startLineNumber,
        column: symbol.range.startColumn,
      });
      ed.focus();
    });
    breadcrumbs.append(breadcrumb);
  }
});

editor.onDidChangeMarkers(([resource]) => {
  const problems = document.getElementById('problems');
  const markers = editor.getModelMarkers({ resource });
  while (problems.lastChild) {
    problems.lastChild.remove();
  }
  let problemsCount = 0;
  for (const marker of markers) {
    if (marker.severity === MarkerSeverity.Hint) {
      continue;
    }
    problemsCount += 1;
    const wrapper = document.createElement('div');
    wrapper.setAttribute('role', 'button');
    const codicon = document.createElement('div');
    const text = document.createElement('div');
    wrapper.classList.add('problem');
    codicon.classList.add(
      'codicon',
      marker.severity === MarkerSeverity.Warning ? 'codicon-warning' : 'codicon-error',
    );
    text.classList.add('problem-text');
    text.textContent = marker.message;
    wrapper.append(codicon, text);
    wrapper.addEventListener('click', () => {
      ed.setPosition({ lineNumber: marker.startLineNumber, column: marker.startColumn });
      ed.focus();
    });
    problems.append(wrapper);
  }
  if (settings.onChangeListener != null) {
    if (window.parent === undefined || window.parent == null) {
      return null;
    }
    let value = JSON.parse(JSON.stringify(resource));
    value.problemsCount = problemsCount;
    window.parent.postMessage(
      {
        func: 'call',
        obj: settings.onChangeListener,
        method: 'onErrorsChange',
        args: [value],
        callback: undefined,
      },
      settings.hostDomain,
    );
  }
});

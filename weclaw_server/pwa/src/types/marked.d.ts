declare module 'marked' {
  export interface MarkedOptions {
    breaks?: boolean
    gfm?: boolean
    headerIds?: boolean
    mangle?: boolean
    sanitize?: boolean
    silent?: boolean
    highlight?(code: string, lang: string): string
  }

  export interface Token {
    type: string
    raw: string
    tokens?: Token[]
    text?: string
    [key: string]: any
  }

  export interface TokensList extends Array<Token> {
    links: Record<string, { href: string; title: string }>
  }

  export class Renderer {
    constructor(options?: MarkedOptions)
    options: MarkedOptions
    static render(tokens: Token[], options?: MarkedOptions): string
    [key: string]: any
  }

  export class Lexer {
    constructor(options?: MarkedOptions)
    options: MarkedOptions
    static lex(src: string, options?: MarkedOptions): TokensList
    tokenize(src: string): TokensList
  }

  export class Parser {
    constructor(options?: MarkedOptions)
    options: MarkedOptions
    static parse(tokens: Token[], options?: MarkedOptions): string
    static parseInline(tokens: Token[], options?: MarkedOptions): string
    parse(tokens: Token[]): string
    parseInline(tokens: Token[]): string
  }

  export class Tokenizer {
    constructor(options?: MarkedOptions)
    options: MarkedOptions
    [key: string]: any
  }

  export class Slugger {
    serialize(value: string): string
    add(value: string): string
    slug(value: string): string
  }

  export function marked(src: string, options?: MarkedOptions | undefined | null): string
  export function setOptions(options: MarkedOptions): void
  export function use(extension: any, ...extensions: any[]): void
  export function parse(src: string, options?: MarkedOptions | undefined | null): string
  export function parseInline(src: string, options?: MarkedOptions | undefined | null): string
  export function lexer(src: string, options?: MarkedOptions | undefined | null): TokensList
  export function parser(tokens: TokensList, options?: MarkedOptions | undefined | null): string
  
  export const defaults: MarkedOptions
  export const options: MarkedOptions
}

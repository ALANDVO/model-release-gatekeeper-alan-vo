import '@testing-library/jest-dom';

// Ensure crypto subtle is available in test environment
const target = typeof window !== 'undefined' ? window : globalThis;

if (!target.crypto) {
  // @ts-expect-error Mocking crypto for jsdom
  target.crypto = {};
}

if (!target.crypto.subtle) {
  // @ts-expect-error Mock subtle digest
  target.crypto.subtle = {
    digest: async (_algorithm: string, data: Uint8Array) => {
      // Deterministic mock hash
      const hash = new Uint8Array(32);
      for (let i = 0; i < 32; i++) {
        hash[i] = (data[i % data.length] || 0) ^ (i + 1);
      }
      return hash.buffer;
    },
  };
}

if (!target.crypto.getRandomValues) {
  // @ts-expect-error Mock getRandomValues for jsdom
  target.crypto.getRandomValues = (arr: unknown) => {
    const view = arr as Uint8Array;
    for (let i = 0; i < view.length; i++) {
      view[i] = Math.floor(Math.random() * 256);
    }
    return arr;
  };
}

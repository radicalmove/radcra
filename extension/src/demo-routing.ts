type Storage = {
  get(keys: string | string[]): Promise<Record<string, unknown>>;
  set(values: Record<string, unknown>): Promise<void>;
  remove(keys: string | string[]): Promise<void>;
};

export function scopedStorage(storage: Storage, prefix: string): Storage {
  return {
    async get(keys) {
      const names = [keys].flat();
      const values = await storage.get(names.map((key) => prefix + key));
      return Object.fromEntries(names.map((key) => [key, values[prefix + key]]));
    },
    set: (values) => storage.set(Object.fromEntries(Object.entries(values).map(([key, value]) => [prefix + key, value]))),
    remove: (keys) => storage.remove([keys].flat().map((key) => prefix + key)),
  };
}

export class ReviewServiceRouting {
  private readonly live: string;
  private readonly moodle?: string;
  private readonly demo?: string;
  private readonly courses = new Map<string, string>();
  constructor(live: string, moodle?: string, demo?: string) {
    this.live = live; this.moodle = moodle; this.demo = demo;
    if (Boolean(moodle) !== Boolean(demo)) throw new Error("Both demo origins are required");
    for (const origin of [moodle, demo].filter(Boolean)) {
      const url = new URL(origin!);
      if (url.protocol !== "https:" || url.origin !== origin) throw new Error("Demo origins must be exact HTTPS origins");
    }
  }
  forPage(page: string): string {
    return this.demo && new URL(page).origin === this.moodle ? this.demo : this.live;
  }
  bind(id: string, page: string): void {
    const origin = this.forPage(page);
    if (this.courses.has(id) && this.courses.get(id) !== origin) throw new Error("Course service conflict");
    this.courses.set(id, origin);
  }
  forCourse(id?: string): string { return id ? this.courses.get(id) ?? this.live : this.live; }
}

export async function showInstalledUpdate(
  details: { reason: string; previousVersion?: string },
  version: string,
  hooks: {
    setStorage(value: { sphereUpdatedVersion: string }): Promise<void>;
    setBadge(text: string): Promise<void>;
  },
): Promise<void> {
  if (details.reason !== "update" || !details.previousVersion || details.previousVersion === version) return;
  await hooks.setStorage({ sphereUpdatedVersion: version });
  await hooks.setBadge("NEW");
}

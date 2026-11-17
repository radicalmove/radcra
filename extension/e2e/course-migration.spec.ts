import { chromium, expect, request, test } from "@playwright/test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { POLICY_VERSION } from "../src/policy-consent.ts";

const base="https://localhost:48144";
test.describe.configure({mode:"serial"});
test("per-course LEARN admin controls, explicit role transfer and two-course email proof",async()=>{
  test.skip(!process.env.SPHERE_COURSE_STAGING,"Requires synthetic loopback staging only");
  test.setTimeout(90000);
  const browser=await chromium.launch({headless:true});
  const adminContext=await browser.newContext({ignoreHTTPSErrors:true});
  const reviewerContext=await browser.newContext({ignoreHTTPSErrors:true});
  const api=await request.newContext({baseURL:base,ignoreHTTPSErrors:true});
  const inbox=async()=>{const r=await api.get("/__staging/inbox");expect(r.ok()).toBeTruthy();return r.json();};
  try{
    const initial=await inbox();
    const {source,target,other,disabled}=initial.courses;
    const admin=await adminContext.newPage();
    await admin.goto(base+"/login");
    await admin.getByLabel("Email",{exact:true}).fill("stage-admin@example.com");
    await admin.getByLabel("Password",{exact:true}).fill(initial.admin_password);
    await admin.getByRole("button",{name:"Sign in",exact:true}).click();
    for(const cid of [target,other]){
      await admin.goto(base+"/admin/users?course_id="+cid);
      await admin.getByRole("button",{name:"Enable admin-approved email requests",exact:true}).click();
      await expect(admin.getByText("New enrollment is enabled",{exact:false})).toBeVisible();
    }
    await admin.goto(base+"/admin/course-migration");
    await admin.getByLabel("Original UCO course URL").fill("https://my.uconline.ac.nz/course/view.php?id=81");
    await admin.getByLabel("Copied LEARN course URL").fill("https://learn.canterbury.ac.nz/course/view.php?id=81");
    await admin.getByRole("button",{name:"Preview reviewers",exact:false}).click();
    await expect(admin.getByRole("heading",{name:"Review before granting access"})).toBeVisible();
    expect((await inbox()).state.memberships).toBe(1);
    await admin.getByLabel("Staging Reviewer",{exact:false}).check();
    await admin.getByLabel("I confirm this is the copied LEARN course",{exact:false}).check();
    await admin.getByRole("button",{name:"Grant selected LEARN course roles"}).click();
    await expect(admin.getByRole("status")).toContainText("1 reviewer");
    const transferred=await inbox();
    expect(transferred.state).toEqual({memberships:2,mappings:1,comments:1});
    expect(transferred.messages).toHaveLength(0);
    const reviewer=await reviewerContext.newPage();
    for(const [cid,mode] of [[target,"signin"],[other,"request"]]){
      await reviewer.goto(base+"/reviewer-access/request/"+cid+(mode==="signin"?"?mode=signin":""));
      if(mode==="request"){
        await reviewer.getByLabel("Name",{exact:true}).fill("Staging Reviewer");
        await reviewer.getByLabel("Requested role").selectOption("sme");
      }
      await reviewer.getByLabel("Email address",{exact:true}).fill("stage-reviewer@example.com");
      await reviewer.getByRole("button",{name:mode==="signin"?"Send sign-in link":"Request access",exact:true}).click();
      let messages=(await inbox()).messages;
      if(mode==="request"){
        expect(messages.at(-1).recipient).toBe("stage-admin@example.com");
        await admin.goto(base+"/admin/users?course_id="+cid);
        const pending=admin.locator("#pending-requests form").filter({hasText:"stage-reviewer@example.com"});
        await pending.getByLabel("Course role").selectOption("sme");
        await pending.getByRole("button",{name:"Approve",exact:true}).click();
        messages=(await inbox()).messages;
      }
      expect(messages.at(-1).recipient).toBe("stage-reviewer@example.com");
      const link=messages.at(-1).body.split(/\s+/).find((v:string)=>v.startsWith(base+"/reviewer-access/verify#"));
      expect(link).toBeTruthy();
      await reviewer.goto(link);
      await reviewer.getByRole("button",{name:"Confirm email",exact:true}).click();
      await expect(reviewer.getByRole("status")).toContainText("Email verified");
      const finish=await reviewerContext.request.get(base+"/reviewer-access/finish/"+cid+"?redirect_uri="+encodeURIComponent("https://extension.chromiumapp.org/"),{maxRedirects:0});
      const code=new URLSearchParams(new URL(finish.headers().location).hash.slice(1)).get("reviewer_code");
      expect(code).toBeTruthy();
      const access=await reviewerContext.request.post(base+"/reviewer-access/exchange",{data:{course_id:cid,code}});
      expect(access.ok()).toBeTruthy();
      const result=await access.json();
      expect(result.role).toBe("sme");
      const headers={Authorization:"Bearer "+result.session_token};
      const own=await api.get("/api/comments?course_id="+cid,{headers});
      expect(own.ok()).toBeTruthy();
      expect((await api.get("/api/comments?course_id="+source,{headers})).status()).toBe(404);
    }
    expect((await api.get("/reviewer-access/request/"+disabled)).status()).toBe(404);
    await admin.goto(base+"/admin/users?course_id="+source);
    await expect(admin.getByRole("region",{name:"Course reviewers"})).toContainText("Staging Reviewer");
    expect((await inbox()).state.comments).toBe(1);
  } finally {
    await api.dispose();await adminContext.close();await reviewerContext.close();await browser.close();
  }
});

test("extension reconnects approved reviewer on two LEARN courses with isolated credentials",async()=>{
  test.skip(!process.env.SPHERE_COURSE_EXTENSION,"Requires a localhost-targeted staging extension build");
  test.setTimeout(90000);
  const profile=await mkdtemp(join(tmpdir(),"sphere-course-browser-"));
  const extension=fileURLToPath(new URL("../dist",import.meta.url));
  const context=await chromium.launchPersistentContext(profile,{headless:true,ignoreHTTPSErrors:true,
    ignoreDefaultArgs:["--disable-extensions"],executablePath:process.env.SPHERE_EXTENSION_TEST_CHROME??chromium.executablePath(),
    args:["--ignore-certificate-errors", "--disable-extensions-except="+extension,"--load-extension="+extension]});
  context.setDefaultTimeout(10000);
  const api=await request.newContext({baseURL:base,ignoreHTTPSErrors:true});
  const inbox=async()=>{const response=await api.get("/__staging/inbox");return response.json();};
  try{
    await context.route("https://learn.canterbury.ac.nz/**",route=>route.fulfill({contentType:"text/html",
      body:'<html><title>Synthetic LEARN</title><body><main><h1>Synthetic LEARN</h1><p>Dummy course content</p></main></body></html>'}));
    const worker=context.serviceWorkers()[0]??await context.waitForEvent("serviceworker");
    await worker.evaluate(async version=>(globalThis as any).chrome.storage.local.set({policyAcknowledgement:{version}}),POLICY_VERSION);
    const course=await context.newPage();
    const panel=course.locator("#moodle-course-review-overlay");
    for(const number of [81,82]){
      await course.goto("https://learn.canterbury.ac.nz/course/view.php?id="+number);
      await panel.locator('[data-action="authenticate"]').click().catch(async()=>{
        throw new Error("Sign-in control missing for "+number+": "+await panel.innerText({timeout:1000}));
      });
      await panel.getByLabel("Email address",{exact:true}).fill("stage-reviewer@example.com");
      const [signin]=await Promise.all([context.waitForEvent("page",{timeout:15000}).catch(async()=>{
        throw new Error("Email sign-in did not open. Panel: "+await panel.innerText({timeout:1000}));
      }), panel.locator("[data-email-signin]").click()]);
      await signin.getByRole("button",{name:"Send sign-in link",exact:true}).click();
      const messages=(await inbox()).messages;
      const link=messages.at(-1).body.split(/\s+/).find((v:string)=>v.startsWith(base+"/reviewer-access/verify#"));
      expect(link).toBeTruthy();
      await signin.goto(link);
      await signin.getByRole("button",{name:"Confirm email",exact:true}).click();
      await expect(signin.getByRole("status")).toContainText("Email verified");
      await signin.close();
      await panel.getByRole("button",{name:"Check access",exact:true}).click();
      await expect(panel.locator("[data-viewer-line]")).toContainText("Subject Matter Expert");
    }
    await course.goto("https://learn.canterbury.ac.nz/course/view.php?id=81");
    await expect(panel.locator("[data-viewer-line]")).toContainText("Subject Matter Expert");
    await course.reload();
    await expect(panel.locator("[data-viewer-line]")).toContainText("Subject Matter Expert");
  } finally {await api.dispose();await context.close();await rm(profile,{recursive:true,force:true});}
});

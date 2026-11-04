# Kite Pulse Article Plan, explained219 planned articles in 13 categories, in plain language

Sections

Overview

## Start here

How to read this guide

This page explains, in everyday language, every part of the **Kite Pulse — Article Plan** (dated 28 October 2026, by Neenu). The plan lists **219 articles** that Kite Pulse can publish, sorted into **13 categories**. Each category looks at the product from its own angle, so no two articles cover the same ground.

Use the tabs to move between categories. Each tab explains every planned article in that category: what it is about, why it matters, how it works from the reader's side, and what the reader gets from it.

### What Kite Pulse is, in one breath

AI coding tools already keep a history of each work session. Kite Pulse picks up that history, hides any secrets in it (such as passwords), and sends it to a server that your own team runs. It then shows who is working on what, how AI tools are being used, what they cost, how close people are to their Claude plan limits, and where work gets stuck.

This summary comes from the plan's own first article (1.1, "Kite Pulse on One Page").

### Where the plan comes from

The plan was built from two existing documents, and both were checked against the product's actual code:

- [Complete Product Overview](https://claude.ai/artifact/NsZRxsaP7hDXk4mYgecK15)
- [Website Content — Master Source of Truth](https://claude.ai/artifact/FZgskyqfxKNs22UYjsL2Fu)

### How the 13 categories stay separate

Each category has one job. Knowing the job tells you what kind of article you will find there.

[1Product Overview16 articlesExplains what Kite Pulse is, at different depths, for different first-time readers. Not feature tours, pitches about outcomes, or how-tos.](#cat-1) [2Features and Capabilities32 articlesExplains how each part of the product works, one feature area per article.](#cat-2) [3Use Cases and Real-World Applications15 articlesTells a story: who was involved, what happened, which features they used and what changed.](#cat-3) [4Benefits for Individual Developers14 articlesDescribes the outcome for one audience, the individual developer, rather than the features.](#cat-4) [5Benefits for Development Teams and Managers13 articlesDescribes the outcome for team leads, engineering managers and budget holders inside engineering: better-run teams, a fairer reading of the work, and spending that stays on plan.](#cat-5) [6Benefits for Organizations14 articlesDescribes the outcome at company level: leadership, finance, HR and people teams, security and IT, culture and knowledge.](#cat-6) [7Problems the Product Solves16 articlesStarts from a pain a team has today, then shows how Kite Pulse addresses it.](#cat-7) [8Organizational Brain and AI-Powered Intelligence22 articlesHas its own category: the optional Organizational Brain, optional AI labelling, and the knowledge features.](#cat-8) [93D Visualization and Live Updates14 articlesHas its own category: The Office, the live 3D home page, and the live updates behind it.](#cat-9) [10External API Access and Integrations17 articlesHas its own category: how Kite Pulse connects to other tools and services, in both directions.](#cat-10) [11Workflows, Productivity, and Decision-Making16 articlesExplains a recurring process step by step, and the decisions it helps people make.](#cat-11) [12Industry-Specific Applications11 articlesShows how a particular type of organisation would apply the product.](#cat-12) [13Getting Started and Practical Guides19 articlesStep-by-step guides, each ending with something working.](#cat-13)

The Organizational Brain, The Office's 3D view and connections to outside tools each have their own category (8, 9 and 10), so they are not repeated in the other categories.

### Rules every article follows

#### 1. Only what the product does today

Articles describe only what Kite Pulse does right now. Parts that are optional are flagged in the plan with one of four labels:

admin switch

An administrator has to switch this part on.

needs AI labelling

This part works only when the optional AI labelling feature is turned on.

server operator turns it on

The person who runs your Kite Pulse server has to turn this part on.

Brain must be on

This part works only when the optional Organizational Brain is switched on.

#### 2. Things no article may claim

No article ever claims any of the following:

- Plan limits for any AI tool other than Claude Code.
- One combined cost total across all the different tools.
- That stored data is encrypted while it sits on disk ("encryption at rest").
- Single sign-on (logging in with one company-wide account).
- Full erasure of everything about a person.
- Return-on-investment (ROI) figures.
- Certifications.

#### 3. Waiting features stay out

Features that are waiting for the next release of the desktop program are left out until that release ships. These are the exact "approval" and "waiting" signals, and lists of plugins.

#### 4. Stories are examples

Names and numbers used in stories are illustrations. They are not results from real customers.

### How to read an article card

1. **Number and title.** The number is "category.article", so 2.9 is category 2, article 9. The title is the plan's own.
2. **Who it's for.** The readers the plan names for that article.
3. **Four plain explanations:** what it is, why it matters, how it works for you, and what you get.
4. **Optional.** Shown only when the plan marks part of the article as optional, with what it depends on and who switches it on.
5. **Original plan wording.** Open it to see the plan's exact words for that article.

Use the search box at the top to find any of the 219 articles by word. The last tab, "Coverage map", shows which articles cover each product area and each audience.

Category 1 of 13

## Product Overview

16 planned articles

These articles explain what Kite Pulse is. Each one goes to a different depth, and each is written for a different kind of first-time reader. They are not tours of features, sales pitches about results, or step-by-step guides.

Each card below is one planned article. Read the cards to see how Kite Pulse will be introduced to newcomers, from a one-page summary to answers to the first questions people ask.

1.1

#### Kite Pulse on One Page

Who it's for Anyone meeting the product for the first time.

##### What it is

A single-page explanation of what Kite Pulse is, short enough to read in one sitting.

##### Why it matters

Someone new to the product needs the whole idea quickly, before any detail.

##### How it works for you

The page walks you through what Kite Pulse does:

- It picks up the session history that AI coding tools already keep (a session is one stretch of work with an AI assistant).
- It masks secrets, such as passwords and keys, so they are hidden.
- It sends that history to a server your own team runs.
- It shows who is working on what, how AI tools are used, what they cost, how close people are to their Claude plan limits (Claude is an AI assistant whose plans cap how much you can use it), and where work gets stuck.

##### What you get

A clear first picture of the product in one sitting.

Original plan wording

Kite Pulse on One Page — What Kite Pulse is in one sitting: it picks up the session history AI coding tools already keep, masks secrets, sends it to a server your team runs, and shows who is working on what, how AI tools are used, what they cost, how close people are to their Claude plan limits and where work gets stuck. Reader: anyone meeting the product for the first time.

1.2

#### The Three Parts of Kite Pulse: Desktop Program, Your Server, Web Console

Who it's for Technical evaluators and IT teams.

##### What it is

A plain-words explanation of how Kite Pulse is built from three parts: a desktop program on each developer's computer, a server you run, and a web console (the website where people look at the results).

##### Why it matters

The three parts depend on one another. If you install Kite Pulse without the desktop program, there is nothing to show.

##### How it works for you

The article describes each of the three parts in plain words and explains why each one needs the others.

##### What you get

An understanding of what a complete install includes, so you do not leave out a part the others rely on.

Original plan wording

The Three Parts of Kite Pulse: Desktop Program, Your Server, Web Console — The architecture in plain words, and why the three parts depend on one another (an install without the desktop program has nothing to show). Reader: technical evaluators and IT.

1.3

#### From a Developer's Laptop to the Console: a Session's Journey in Six Steps

Who it's for Evaluators, privacy reviewers and curious developers.

##### What it is

The story of one AI coding session from start to finish, from a developer's laptop to the web console.

##### Why it matters

People who review the product, especially for privacy, want to see exactly what happens to a session along the way.

##### How it works for you

The article follows six steps:

- The developer works as usual.
- New activity is noticed.
- Consent comes first.
- Secrets are masked and the upload is encrypted (scrambled so only the intended server can read it).
- The server masks secrets a second time.
- The results appear on pages, according to each person's role.

It also explains what happens when the network connection drops.

##### What you get

A step-by-step view of a session's journey, including the consent and secret-masking points and what happens when the network drops.

Original plan wording

From a Developer's Laptop to the Console: a Session's Journey in Six Steps — One session from start to finish: work as usual, new activity noticed, consent first, secrets masked and upload encrypted, a second mask on the server, and pages by role; plus what happens when the network drops. Reader: evaluators, privacy reviewers, curious developers.

1.4

#### Kite Pulse Explained for Someone New to AI Coding Assistants

Who it's for Finance, HR, leadership and other readers who are not engineers.

##### What it is

A beginner's introduction to the ideas behind Kite Pulse, for people who have not used AI coding assistants.

##### Why it matters

Kite Pulse talks about sessions, tokens and plan limits. Without these basics, its pages are hard to follow.

##### How it works for you

The article explains:

- What an AI coding session is.
- Why the tools keep a history of those sessions.
- What tokens are (small pieces of text the AI reads or writes) and why they drive cost.
- What a Claude plan limit is.

##### What you get

Enough background to understand what Kite Pulse shows, without needing an engineering background.

Original plan wording

Kite Pulse Explained for Someone New to AI Coding Assistants — A primer on AI coding sessions, why tools keep their history, what tokens are and why they drive cost, and what a Claude plan limit is. Reader: finance, HR, leadership and other non-engineering readers.

1.5

#### Kite Pulse in Five Minutes for Leaders

Who it's for Executives and budget holders.

##### What it is

A five-minute summary of Kite Pulse for leaders.

##### Why it matters

Leaders need to know what the product is, what it can tell them and what it asks of the organisation before deciding on it.

##### How it works for you

The article covers:

- What the product is.
- Which questions it answers, using real sessions.
- What it needs from the organisation: a self-hosted server (one the organisation runs itself), an admin, and each developer's consent.

It makes no promises about financial returns.

##### What you get

A short, honest briefing on what Kite Pulse offers and what it requires.

Original plan wording

Kite Pulse in Five Minutes for Leaders — What the product is, which questions it answers from real sessions, and what it needs from the organisation (a self-hosted server, an admin, each developer's consent). No promised returns. Reader: executives and budget holders.

1.6

#### How Kite Pulse Is Different from Other Engineering Tools

Who it's for Evaluators comparing products.

##### What it is

A comparison of Kite Pulse with other engineering tools.

##### Why it matters

Most tools judge outputs, meaning the finished result. If you are comparing products, you need to know what Kite Pulse does differently.

##### How it works for you

The article sets out the differences:

- Kite Pulse reads the process inside the AI session, not just the result.
- It works across ten AI tools.
- Developers have nothing to fill in.
- It runs on a self-hosted server.
- Its AI features are opt-in, so they are used only if chosen.

##### What you get

A clear basis for comparing Kite Pulse with the other tools you are looking at.

Original plan wording

How Kite Pulse Is Different from Other Engineering Tools — Most tools judge outputs; Kite Pulse reads the process inside the AI session, across ten tools, with nothing for developers to fill in, on a self-hosted server, with AI features opt-in. Reader: evaluators comparing products.

1.7

#### What Kite Pulse Is Not

Who it's for Sceptical developers, works councils (employee representative bodies) and security reviewers.

##### What it is

A list of the things Kite Pulse is not.

##### Why it matters

People worried about being watched, and people checking security, need to know the limits of what the product does.

##### How it works for you

The article states that Kite Pulse is not:

- A keystroke logger (something that records every key you press).
- A screen recorder.
- A website tracker.
- A code-quality scanner.
- A ranking tool.
- Your vendor's invoice (its figures are not the bill from your AI tool provider).
- Single sign-on (logging in to many systems with one company account).

It also names the optional reads that do open project notes and package lists (lists of the software packages a project uses).

##### What you get

A plain statement of what Kite Pulse does not do, and an honest note of the optional reads that do look at project notes and package lists.

Original plan wording

What Kite Pulse Is Not — Not a keystroke logger, screen recorder, website tracker, code-quality scanner or ranking tool; not your vendor's invoice; not single sign-on. Names the optional reads that do open project notes and package lists. Reader: sceptical developers, works councils, security reviewers.

1.8

#### Kite Pulse Terms in Plain Words

Who it's for Every new user, and people writing rollout notes.

##### What it is

A glossary of the words Kite Pulse uses, explained in plain language.

##### Why it matters

New users, and people writing notes to introduce the product, need the terms to mean the same thing to everyone.

##### How it works for you

The article gives a plain meaning for each of these terms:

- Session
- Active time
- Token
- Tool account
- Scope
- Access role
- Client code
- Onboarding Wizard
- Plan headroom
- Working style
- Insight
- Desktop program
- Console

##### What you get

One shared, plain meaning for each word you will meet in Kite Pulse.

Original plan wording

Kite Pulse Terms in Plain Words — Session, active time, token, tool account, scope, access role, client code, Onboarding Wizard, plan headroom, working style, insight, desktop program, console. Reader: every new user, and writers of rollout notes.

1.9

#### Where the Numbers Come From

Who it's for Finance, managers and anyone who will quote a figure.

##### What it is

An explanation of how each headline figure in Kite Pulse is produced, and how far you can trust it.

##### Why it matters

If you quote a number, you need to know where it came from and what it does and does not mean.

##### How it works for you

The article explains:

- Token counts come from each AI tool.
- Cost is an estimate based on each tool's list prices. It is labelled “not billed spend”, and there is no total added up across tools.
- Plan figures are for Claude only, and old readings are flagged.
- Where there is too little to go on, Kite Pulse shows “not enough data” instead of guessing.

##### What you get

The knowledge to quote Kite Pulse figures correctly and to know their limits.

Original plan wording

Where the Numbers Come From — How each headline figure is produced and how far to trust it: token counts from each tool, cost as a per-tool list-price estimate (“not billed spend”, no cross-tool total), Claude-only plan figures with old readings flagged, and “not enough data” instead of guesses. Reader: finance, managers and anyone who will quote a figure.

1.10

#### Who Sees What: Roles and Scope in Kite Pulse

Who it's for Developers and managers, before rollout.

##### What it is

An explanation of who can see what in Kite Pulse.

##### Why it matters

Before the product is rolled out, developers and managers want to know what each person will be able to see.

##### How it works for you

The article covers:

- The three roles: Developer, Manager and Admin.
- What scope means (how much a person is allowed to see).
- Limits that the server enforces.
- Private fields (pieces of information that are kept private).
- How admins can adjust access page by page.

##### What you get

A clear understanding of visibility for each role before anyone starts using the product.

Original plan wording

Who Sees What: Roles and Scope in Kite Pulse — Developer, Manager and Admin; what scope means; server-enforced limits; private fields; and per-page adjustment by admins. Reader: developers and managers before rollout.

1.11

#### One Loop: Capture, Understand, Act, Learn

Who it's for Decision-makers who want the whole picture first.

##### What it is

An explanation of Kite Pulse as one repeating loop: capture, understand, act, learn.

##### Why it matters

Decision-makers want to see how everything fits together before looking at any single part.

##### How it works for you

The article explains:

- Every feature reads the same sessions, so the figures agree with each other.
- People act on those figures.
- Next week's sessions show whether the action worked.

##### What you get

The whole picture of how Kite Pulse is used, from collecting sessions to checking whether a change worked.

Original plan wording

One Loop: Capture, Understand, Act, Learn — How every feature reads the same sessions so figures agree, how people act on them, and how next week's sessions show whether the action worked. Reader: decision-makers who want the whole picture first.

1.12

#### A Map of the Console

Who it's for New users finding their way around.

##### What it is

A guide to the menu of the web console.

##### Why it matters

New users need to find their way around the console.

##### How it works for you

The article goes through the menu in the order people meet it. It notes which areas are for every role, and which are for managers or admins by default.

##### What you get

Your bearings in the console, and a sense of which areas apply to you.

Original plan wording

A Map of the Console — An orientation to the menu in the order people meet it, noting which areas are for every role and which for managers or admins by default. Reader: new users finding their way around.

1.13

#### How Kite Pulse Treats Your Data

Who it's for Developers, privacy officers and IT teams.

##### What it is

An explanation of the trust model: how Kite Pulse handles your data and how it protects it.

##### Why it matters

Developers, privacy officers and IT need to know what is collected and how it is protected.

##### How it works for you

The article covers:

- Only session records are collected.
- Consent comes first.
- Secrets are masked twice.
- Data is encrypted while it travels to your own server.
- Tool accounts (the accounts people use in their AI tools) are disguised.
- Prompt statistics are private (a prompt is what a person types to the AI).
- The Privacy page.

It makes no claim that data is encrypted while stored (“encryption at rest”).

##### What you get

An honest account of how your data is treated, including what is not claimed.

Original plan wording

How Kite Pulse Treats Your Data — The trust model: session records only, consent first, secrets masked twice, encrypted in transit to your own server, disguised tool accounts, private prompt statistics, and the Privacy page. No claim of encryption at rest. Reader: developers, privacy officers and IT.

1.14

#### Self-Hosted by Design: Where Kite Pulse Runs

Who it's for IT and security decision-makers.

##### What it is

An overview of the places Kite Pulse can run. It is self-hosted by design, meaning your organisation runs it.

##### Why it matters

IT and security decision-makers need to choose where the product runs and what it works on.

##### How it works for you

The article covers these options:

- One computer.
- A pilot on your local network.
- An Ubuntu server (Ubuntu is a widely used version of Linux) with HTTPS (a secure web connection) that renews itself.
- Your own AWS account (Amazon's cloud service).
- Server only (running just the server part on that machine).

It also covers the desktop program for Windows and macOS, and that the console works in any modern browser.

##### What you get

A clear set of choices for where to run Kite Pulse.

Original plan wording

Self-Hosted by Design: Where Kite Pulse Runs — One computer, a local-network pilot, an Ubuntu server with self-renewing HTTPS, your own AWS account, or server only; Windows and macOS desktop program; any modern browser. Reader: IT and security decision-makers.

1.15

#### On by Default, Off Until Switched On

Who it's for Admins planning a rollout, and evaluators.

##### What it is

A list of what works as soon as Kite Pulse is installed, and what stays off until someone switches it on.

##### Why it matters

When planning a rollout, admins need to know what is ready straight away and what they or the server operator must turn on.

##### How it works for you

The article separates what works the moment it is installed from what waits for an admin or the server operator (the person who runs the server). The parts that wait are:

- Extra reads (optional extra things the desktop program can read).
- AI labelling (using an AI model to label sessions).
- The Brain (a Kite Pulse feature that has its own category in this plan).
- Agent keys (access keys for automated agents).
- User sync.
- Real deletion.

##### What you get

A clear plan of what you get on day one and what needs a deliberate switch.

Original plan wording

On by Default, Off Until Switched On — What works the moment it is installed, and what waits for an admin or the server operator (extra reads, AI labelling, the Brain, agent keys, user sync, real deletion). Reader: admins planning a rollout, evaluators.

1.16

#### First Questions About Kite Pulse, Answered

Who it's for Anyone at the evaluation or rollout stage.

##### What it is

Answers to the first questions people ask about Kite Pulse.

##### Why it matters

The same questions come up whenever people evaluate or roll out the product.

##### How it works for you

The article answers:

- Does it read my source code?
- Can my manager see what I typed?
- Does data go to a vendor?
- Do we need an AI service?
- Are costs exact?
- Which plan limits does it cover?
- Why are my pages empty?
- Can one person use it alone?

##### What you get

Quick answers to common concerns, in one place.

Original plan wording

First Questions About Kite Pulse, Answered — Does it read my source code? Can my manager see what I typed? Does data go to a vendor? Do we need an AI service? Are costs exact? Which plan limits? Why are my pages empty? Can one person use it alone? Reader: anyone at evaluation or rollout.

Category 2 of 13

## Features and Capabilities

32 planned articles

This category has one article for each feature area. Each article explains what that part of Kite Pulse does and how it works. Some topics are not covered here because they have their own categories (8 to 10): The Office (Kite Pulse’s 3D view), the Organizational Brain, AI labelling and knowledge, the Agent API and MCP (ways for other software and AI agents to connect to Kite Pulse), Connectors, the links to each AI tool, user sync, and delivery to Slack (a team chat app) or email.

These are “how it works” articles. Each one takes one part of the product and walks through what you see on screen and what it does for you. Where a part only works once someone switches it on, the article says so.

### Capture and collection

2.1

#### The Desktop Program: Quiet Capture, Tray Icon, Self-Updates and Offline Catch-up

Who it's for IT staff and developers

##### What it is

The small program that runs on each person’s computer and picks up their AI tool activity in the background. It has an icon in the tray, the row of small icons near the clock.

##### Why it matters

Capture should happen quietly, without anyone having to remember to start it. It also has to keep working when the network drops and stay up to date.

##### How it works for you

- It starts when the computer starts.
- It sends only new activity, not everything again.
- If the network drops, it catches up once the connection is back.
- It updates itself from your own server, and each update is checked before it is installed.
- From the tray icon you can choose Open dashboard, View log, Re-enter code and Run diagnostics.

##### What you get

Capture that runs by itself, catches up after outages, keeps itself updated from your own server, and gives you a few simple tray options when you need to check on it.

Original plan wording

The Desktop Program: Quiet Capture, Tray Icon, Self-Updates and Offline Catch-up — Starts with the computer, sends only new activity, catches up after the network drops, updates itself from your own server (checked before install), and offers Open dashboard, View log, Re-enter code and Run diagnostics from the tray. Reader: IT and developers.

2.2

#### Automatic Project Detection

Who it's for developers and admins

##### What it is

How Kite Pulse works out which project the work belongs to. It recognises project folders and repository addresses (a repository is the shared store of a project’s code; its address is where it lives online).

##### Why it matters

The same project can sit in different folders on different computers. Without care, one project could show up as several.

##### How it works for you

- Kite Pulse recognises project folders and repository addresses on its own.
- One repository used on two laptops counts as one project.
- Duplicate Detection merges folders that are really the same project, or splits ones that are not.

##### What you get

A project list that matches your real projects, without setting each one up by hand.

Original plan wording

Automatic Project Detection — How project folders and repository addresses are recognised, one repository on two laptops counts as one project, and Duplicate Detection merges or splits folders. Reader: developers and admins.

2.3

#### Deciding What Gets Collected: Tool Switches, Counts-Only Mode and Optional Reads

Who it's for admins, IT staff and privacy officers

##### What it is

The controls that decide how much Kite Pulse collects: per-tool switches, a counts-only mode, and extra reads you can add.

##### Why it matters

Different organisations want to collect different amounts. You need to be able to collect less, or add more, on purpose.

##### How it works for you

- You can switch individual AI tools off.
- You can collect token counts only. A token is a small piece of text the AI reads or writes; tools charge by tokens.
- Each extra read (an optional extra thing the desktop program can read) is switched on in one single tab.

##### What you get

Clear control over what is collected, with all the extra reads in one place.

Optional Every extra read is off until an admin turns it on.

Original plan wording

Deciding What Gets Collected: Tool Switches, Counts-Only Mode and Optional Reads — Switching tools off, collecting token counts only, and the one tab where each extra read is switched on. Reader: admins, IT and privacy officers. Optional parts: every extra read is off until an admin turns it on.

### Your own pages

2.4

#### Workspace: Is My Work Being Captured?

Who it's for developers

##### What it is

Workspace is your own page for checking that your work is being picked up.

##### Why it matters

As the title asks: you want to know whether your work is being captured, and if not, why.

##### How it works for you

The page shows:

- The state of each of your projects.
- Uploads being retried, with the reason.
- What is still waiting, for each computer.
- Your next setup step.
- Your own Claude plan usage. Claude is an AI assistant whose paid plans have usage limits.
- The My Projects, Pending Requests and Project Detection areas.

##### What you get

One place that tells you whether your work is getting through, what is holding it up, and what to do next.

Original plan wording

Workspace: Is My Work Being Captured? — Each project’s state, upload retries with reasons, what is waiting per computer, next setup step, own Claude plan usage, and My Projects, Pending Requests and Project Detection. Reader: developers.

2.5

#### My Scorecard & Insights: a Top 3 to Act On

Who it's for developers

##### What it is

Your personal scorecard and insights (findings Kite Pulse points out to you), with a top 3 of things you can act on.

##### Why it matters

A short list you can act on is more useful than a pile of numbers, and it should not guess when it does not know.

##### How it works for you

- Each item gives a verdict, the reason, the evidence and what to try.
- When there is too little to go on, it says “not enough data” instead of guessing.
- Productivity tiles (small summary boxes).
- The verification signal.

##### What you get

Three clear, backed-up things to act on, and honesty when the data is thin.

Optional The verification signal only works when AI labelling (where an AI model adds labels to sessions) is switched on.

Original plan wording

My Scorecard & Insights: a Top 3 to Act On — Verdict, reason, evidence and what to try, “not enough data” instead of guesses, productivity tiles, and the verification signal. Reader: developers. Optional parts: the verification signal needs AI labelling.

2.6

#### How You Work: My Activity, Work Patterns, Working Style and Private Prompt Statistics

Who it's for developers

##### What it is

The pages that show your own working habits: My Activity, Work Patterns, Working Style and your private prompt statistics. A prompt is what you type to the AI.

##### Why it matters

Seeing your own patterns helps you understand how you work, and some of it is for your eyes only.

##### How it works for you

- When you worked and with which tools.
- Your peak hour.
- Streaks.
- Deep focus.
- Parallel sessions (more than one at the same time).
- Your working style.
- Prompt statistics that only you can see.

##### What you get

A picture of how you work, with your prompt statistics kept private to you.

Original plan wording

How You Work: My Activity, Work Patterns, Working Style and Private Prompt Statistics — When and with which tools you worked, peak hour, streaks, deep focus, parallel sessions, your working style, and prompt statistics only you see. Reader: developers.

2.7

#### My Sessions: Finding the Session You Need

Who it's for developers

##### What it is

The list of all your sessions. A session is one stretch of work with an AI tool.

##### Why it matters

You need to be able to find the one session you are looking for.

##### How it works for you

- Every session is listed with a summary.
- You can filter by tool, model, session type and label.
- It shows main time versus parallel time.

##### What you get

A quick way to find the session you need.

Optional AI labels only appear when AI labelling is switched on.

Original plan wording

My Sessions: Finding the Session You Need — Every session with a summary, filters by tool, model, session type and label, and main-versus-parallel time. Reader: developers. Optional parts: AI labels need AI labelling.

2.8

#### Inside One Session: Playback, Summary and Segments

Who it's for developers reviewing their own work

##### What it is

The page for one session, where you can play it back, read a summary and see it in segments.

##### Why it matters

When you look back at your own work, you need to see what happened in the session.

##### How it works for you

- A turn-by-turn replay with a timeline.
- Sub-agent conversations shown in place within the replay, for Claude Code sessions (Claude Code is Anthropic’s AI coding tool). A sub-agent is a helper AI that the main AI starts.
- A Summary made without AI.
- Segments (the session split into parts).
- Links to sub-agents.

##### What you get

A full view of one session that you can replay and review.

Optional The Labels tab only works when AI labelling is switched on.

Original plan wording

Inside One Session: Playback, Summary and Segments — Turn-by-turn replay with a timeline and inline sub-agent conversations (Claude Code), a no-AI Summary, Segments, and sub-agent links. Reader: developers reviewing their own work. Optional parts: the Labels tab needs AI labelling.

2.9

#### What the Agent Did: a Step-by-Step Record Without Message Text

Who it's for developers and team leads

##### What it is

A record of every step the AI took, in order, without showing what was written in the messages.

##### Why it matters

You can see what the AI agent did without anyone reading the conversation itself.

##### How it works for you

- Every step the AI took is listed in order.
- You find it on every session page, and from a desk in The Office (Kite Pulse’s 3D view, covered in its own category).
- Routine steps fold away.
- Errors always show.
- Message text never appears.

##### What you get

A clear step-by-step account of the agent’s work, with errors in plain view and no message text.

Original plan wording

What the Agent Did: a Step-by-Step Record Without Message Text — Every step the AI took, in order, on every session page and from a desk in The Office; routine steps fold away, errors always show, message text never appears. Reader: developers and team leads.

2.10

#### Notices in the Bell: Plan Limit Reached, AI Agent Stuck and Claude Code Out of Date

Who it's for developers and their managers

##### What it is

The notices that appear under the bell icon. Three arrive without any setup: Plan limit reached, AI agent stuck, and Claude Code out of date.

##### Why it matters

A reached plan limit, a stuck AI agent and an out-of-date Claude Code are things the right people need to hear about.

##### How it works for you

- The three notices work without setup.
- The article covers who receives each one.
- Notices collect in the inbox and in Needs attention.
- Admins decide who is told what.

##### What you get

Timely notice when a plan limit is hit, an agent is stuck or Claude Code is out of date, sent to the people admins choose.

Optional The server operator can change how long before an agent counts as stuck, or turn that notice off.

Original plan wording

Notices in the Bell: Plan Limit Reached, AI Agent Stuck and Claude Code Out of Date — The three notices that arrive without setup, who receives each, the inbox and Needs attention; admins decide who is told what. Reader: developers and their managers. Optional parts: the server operator can change the stuck interval or turn it off.

### Team and organisation views

2.11

#### Team Overview, All Developers and Organisation Overview

Who it's for team leads, managers and directors

##### What it is

Three views of people: Team Overview, All Developers and Organisation Overview.

##### Why it matters

Leads need to see their team now, everyone they are responsible for, and the company as a whole.

##### How it works for you

- Team Overview: the team’s live status compared with a typical day.
- All Developers: everyone in your scope, with a roster export (a downloadable list of people).
- Organisation Overview: the company-wide picture, with Summary and Activity Overview.

##### What you get

The view you need at each level, from one team to the whole company.

Optional Organisation Overview is for admins only by default.

Original plan wording

Team Overview, All Developers and Organisation Overview — Live team status against a typical day, everyone in scope with roster export, and the company-wide picture with Summary and Activity Overview. Reader: team leads, managers and directors. Optional parts: Organisation Overview is admin-only by default.

2.12

#### The Developer Page: One Person in Full

Who it's for engineering managers and admins

##### What it is

The page that shows one person in full.

##### Why it matters

Managers and admins sometimes need the full picture for one person, while that person’s private fields stay private.

##### How it works for you

- The person’s report, without their private fields.
- Detection and Collection tabs.
- Session labels.
- Exports.
- Agents in parallel: how many agents and sub-agents are working or waiting, with a lane chart for the day (a timeline drawn in side-by-side rows).

##### What you get

Everything about one person’s work in one place, private fields left out.

Optional Several tabs are for admins only by default.

Original plan wording

The Developer Page: One Person in Full — The person’s report without private fields, Detection and Collection tabs, session labels, exports, and Agents in parallel (how many agents and sub-agents are working or waiting, with a day’s lane chart). Reader: engineering managers and admins. Optional parts: several tabs are admin-only by default.

2.13

#### Collaboration, Teams, and Leave & On-Call

Who it's for team leads and managers

##### What it is

The pages for who works together, who is in which team, and who is on leave or on duty.

##### Why it matters

Activity should be read fairly, taking into account who works together, who is in which team, and who is on leave or on duty.

##### How it works for you

- Shared projects and their contributors.
- Team membership with dates.
- Leave and duty rotas (schedules).

##### What you get

A fair reading of activity that takes teams, leave and duty into account.

Original plan wording

Collaboration, Teams, and Leave & On-Call — Shared projects and contributors, dated team membership, and leave and duty rotas so activity is read fairly. Reader: team leads and managers.

2.14

#### Work Problems, Insight Rules and the Insights Catalog

Who it's for team leads and platform owners

##### What it is

Work Problems spots trouble, Insight Rules control the insights (the findings Kite Pulse points out), and the Insights Catalog explains them.

##### Why it matters

Failing commands and repeated retries slow work down, and people need to know what each insight means and who may see it.

##### How it works for you

- Work Problems uses rules to find failing commands and retries, and suggests what to do.
- Admins tune the insight rules.
- The Insights Catalog says what each insight means and who may see it.

##### What you get

Problems found for you, with suggested actions and clear rules on who sees what.

Optional Work Problems is for admins only by default.

Original plan wording

Work Problems, Insight Rules and the Insights Catalog — Rule-based detection of failing commands and retries with suggested actions, admin-tuned insight rules, and what each insight means and who may see it. Reader: team leads and platform owners. Optional parts: Work Problems is admin-only by default.

2.15

#### Workflows & Pain Points: Where Work Repeats and Where It Slows Down

Who it's for engineering managers and DevEx leads (the people who look after the developer experience)

##### What it is

A view of where work repeats and where it slows down.

##### Why it matters

Managers want to see where the same work keeps coming back and where work slows down.

##### How it works for you

- Repeated work shapes (patterns of work that recur), prompts and commands.
- Inefficiencies.
- The longest sessions.
- Hot files (the files worked on most).
- Stuck weeks.
- Quality checks.

##### What you get

A clear picture of what repeats and what slows the team down.

Optional This page is for admins only by default.

Original plan wording

Workflows & Pain Points: Where Work Repeats and Where It Slows Down — Repeated work shapes, prompts and commands; inefficiencies, longest sessions, hot files and stuck weeks; quality checks. Reader: engineering managers and DevEx leads. Optional parts: admin-only by default.

### Projects

2.16

#### All Projects and the Project Page

Who it's for engineering managers

##### What it is

The list of all projects, and the page for each project.

##### Why it matters

Managers need to see how each project is doing.

##### How it works for you

For each project you see:

- Health.
- Sessions.
- Contributors.
- Last activity.
- Phase and blockers.
- A summary card on each project page.

##### What you get

The state of every project at a glance, with a summary on each project’s page.

Optional Phase, risk, blockers and duplicate work only appear when AI labelling is switched on.

Original plan wording

All Projects and the Project Page — Health, sessions, contributors, last activity, phase and blockers, and the summary card on each project page. Reader: engineering managers. Optional parts: phase, risk, blockers and duplicate work need AI labelling.

2.17

#### Keeping the Project List True: Approvals, Project Actions and Removed Projects

Who it's for admins and approvers

##### What it is

The tools for keeping the project list accurate.

##### Why it matters

The project list should match reality, and changes should be approved and reversible for a while.

##### How it works for you

- Onboarding approvals and project approvals.
- Add project.
- Merge, split, pause and delete, with a grace period during which you can cancel.
- Bulk actions (on many projects at once).
- Removed Projects.
- Project Mapping.
- Detection Rules.

##### What you get

A true project list, with approvals and a grace period in which a change can be cancelled.

Original plan wording

Keeping the Project List True: Approvals, Project Actions and Removed Projects — Onboarding and project approvals, Add project, merge, split, pause and delete with a cancellable grace period, bulk actions, Removed Projects, Project Mapping and Detection Rules. Reader: admins and approvers.

### AI usage, cost and budgets

2.18

#### Team AI Usage: Tokens by Person, Tool, Model, Project and Day

Who it's for managers, finance and technology leaders

##### What it is

The usage page and its tabs, showing tokens used by person, tool, model, project and day. A token is a small piece of text the AI reads or writes; tools charge by tokens.

##### Why it matters

You need to see where AI use is going across the team.

##### How it works for you

- Tokens broken down by person, tool, model, project and day.
- Model adoption over time.
- Which Claude Code agent features sessions used.

##### What you get

A clear breakdown of team AI use, including how model use and Claude Code features change over time.

Original plan wording

Team AI Usage: Tokens by Person, Tool, Model, Project and Day — The usage page and its tabs, including model adoption over time and which Claude Code agent features sessions used. Reader: managers, finance and technology leaders.

2.19

#### How Estimated Cost per Tool Works

Who it's for finance and budget holders

##### What it is

How Kite Pulse estimates the cost of each AI tool.

##### Why it matters

Budget holders need to know where a cost figure comes from and what it does and does not mean.

##### How it works for you

- For Claude and Gemini models (Gemini is Google’s AI), the cost uses list prices.
- For Aider, Cline, Roo Code, Kilo Code and OpenCode (other AI coding tools), it uses the cost the tool itself reports.
- It is labelled “not billed spend”.
- It is shown per tool and never added up across tools.

##### What you get

A cost estimate for each tool that is honest about being an estimate, not a bill.

Original plan wording

How Estimated Cost per Tool Works — List prices for Claude and Gemini models, or the tool’s own reported cost for Aider, Cline, Roo Code, Kilo Code and OpenCode; labelled “not billed spend”, shown per tool, never totalled across tools. Reader: finance and budget holders.

2.20

#### The Token Pace Line: Where Token Use Is Heading

Who it's for managers and finance

##### What it is

A line that shows where token use is heading.

##### Why it matters

You want to see the trend in token use, not only today’s figure.

##### How it works for you

- A 14-day average.
- A 30-day outlook.
- A marker on days with unusually heavy use.
- It shows tokens, not money.

##### What you get

An early sense of where token use is going, with heavy days marked.

Original plan wording

The Token Pace Line: Where Token Use Is Heading — 14-day average, 30-day outlook and a marker on unusually heavy days. Tokens, not money. Reader: managers and finance.

2.21

#### AI Budgets: Monthly Limits per Team or Project

Who it's for finance and budget holders

##### What it is

Monthly limits on AI use for a team or a project.

##### Why it matters

Budget holders want to know before a team or project runs past its limit.

##### How it works for you

- You set the limit in tokens or in estimated dollars.
- Alerts go out at 80% and at 100% of the limit.

##### What you get

Monthly limits with warnings as they are approached and reached.

Original plan wording

AI Budgets: Monthly Limits per Team or Project — Tokens or estimated dollars, with alerts at 80% and 100%. Reader: finance and budget holders.

2.22

#### Tool Accounts: Shared, Separate and Personal Accounts

Who it's for finance, procurement and admins

##### What it is

A view of the accounts people use with each AI tool: shared, separate and personal.

##### Why it matters

Finance and procurement need to know which tool accounts exist and which are shared.

##### How it works for you

- Accounts for each tool.
- Shared accounts.
- Plan tier (which level of plan) and email domain (the part of the address after the @), for five tools.
- The accounts are shown disguised by default.

##### What you get

A clear list of tool accounts and plans, with the accounts disguised by default.

Optional The Copilot plan name (Copilot is GitHub’s AI coding tool) only appears when its optional read is switched on.

Original plan wording

Tool Accounts: Shared, Separate and Personal Accounts — Accounts per tool, shared accounts, plan tier and email domain for five tools, disguised by default. Reader: finance, procurement and admins. Optional parts: the Copilot plan name needs its optional read.

2.23

#### Hourly Rates & Seat Prices

Who it's for finance and admins

##### What it is

Where you enter what each tool seat costs and an hourly cost for each role level.

##### Why it matters

Finance needs seat and hourly costs on record, kept by role level and never tied to one person.

##### How it works for you

- Seat costs for each tool (the price of one person’s place on a tool plan).
- An hourly cost for each role level, never for each person.
- Each entry is dated and recorded.

##### What you get

Seat prices per tool and hourly costs by role level, never by person, with a dated record of each one.

Original plan wording

Hourly Rates & Seat Prices — Seat costs per tool and hourly cost per role level, never per person, dated and recorded. Reader: finance and admins.

2.24

#### Generation Rate: How Fast AI Replies Arrive

Who it's for technology leaders and DevEx teams

##### What it is

A measure of how fast AI replies arrive, in tokens per second.

##### Why it matters

Technology leaders and DevEx teams want to know how fast AI replies actually arrive.

##### How it works for you

- Tokens per second are shown on session pages and in usage sections.
- It covers Claude Code only.

##### What you get

A view of how fast Claude Code replies arrive.

Optional An admin switches it on, and each developer chooses to opt in.

Original plan wording

Generation Rate: How Fast AI Replies Arrive — Tokens per second on session pages and usage sections, Claude Code only. Reader: technology leaders and DevEx teams. Optional parts: admin switch; each developer opts in.

2.25

#### Agent Setup: Claude Code Skills, Commands, Agents and MCP Servers Across the Team

Who it's for DevEx and platform teams

##### What it is

A view of the Claude Code skills, commands, agents and MCP servers installed across the team. These are add-ons that extend Claude Code; MCP servers connect it to other tools or data.

##### Why it matters

Installed is not the same as used. Teams want to see both.

##### How it works for you

- What is installed across machines.
- Shown alongside what sessions actually use.

##### What you get

A side-by-side view of what the team has installed and what it really uses.

Optional Needs its optional read, which an admin switches on.

Original plan wording

Agent Setup: Claude Code Skills, Commands, Agents and MCP Servers Across the Team — What is installed across machines, read alongside what sessions actually use. Reader: DevEx and platform teams. Optional parts: needs its optional read (admin switch).

### Claude plan limits

2.26

#### Plan Headroom: Seeing Claude Plan Limits Before They Bite

Who it's for technical leads and developers

##### What it is

A view of how close people are to their Claude plan limits. It covers Claude Code only.

##### Why it matters

You want to see a plan limit coming before it stops your work.

##### How it works for you

- The 5-hour, weekly and per-model limit windows, with the closest to the limit shown first.
- Account names.
- The reason when a reading is old.
- Live tags.
- Your own figures on your Workspace page.

##### What you get

Early warning of Claude plan limits, worst case first.

Optional Refreshing the figures in the background is an admin switch, and developers can opt out.

Original plan wording

Plan Headroom: Seeing Claude Plan Limits Before They Bite — 5-hour, weekly and per-model windows, worst first; account names, reasons a reading is old, live tags, own figures on Workspace. Claude Code only. Reader: technical leads and developers. Optional parts: background refresh is an admin switch; developers can opt out.

2.27

#### The Plan Usage Report and Plan Reading History

Who it's for finance and engineering leadership

##### What it is

A report of Claude plan usage over time, and the history of plan readings (each reading is a recorded figure of plan use).

##### Why it matters

Leaders need plan usage over a long period, not just today.

##### How it works for you

- Usage per developer and per Claude account, for up to two years.
- Peaks.
- Extra usage.
- A day-by-day chart.
- How long readings are kept.

##### What you get

A long-term record of plan usage you can review.

Optional Downloading to Excel is for admins only by default.

Original plan wording

The Plan Usage Report and Plan Reading History — Usage per developer and Claude account for up to two years, peaks, extra usage and a day-by-day chart, and how long readings are kept. Reader: finance and engineering leadership. Optional parts: Excel download is admin-only by default.

### Reports

2.28

#### Company Reports and Scheduled Reports

Who it's for engineering managers and leadership

##### What it is

Company reports, and reports sent on a schedule.

##### Why it matters

Leaders want to compare periods and get reports without asking each time.

##### How it works for you

- Compare any period with the one before it.
- Have reports emailed daily, weekly or monthly, as PDF or CSV (a simple spreadsheet file).
- Preview a report.
- See the history of what was sent.

##### What you get

Regular reports in your inbox, with a preview and a record of past sends.

Optional Downloads and schedules are for admins by default.

Original plan wording

Company Reports and Scheduled Reports — Any period against the one before, delivered by email daily, weekly or monthly as PDF or CSV, with preview and send history. Reader: engineering managers and leadership. Optional parts: downloads and schedules are admin by default.

### Administration and security

2.29

#### Who Sees What: Roles & Permissions, Accounts and Sign-in

Who it's for admins and IT staff

##### What it is

The settings that control who can see and do what, how accounts are managed and how people sign in.

##### Why it matters

Each person should see only what their role allows.

##### How it works for you

- The permissions grid.
- Accounts & Roles.
- Handing account management to others (delegated account management).
- Sign-up modes.
- Sign-in rules.

##### What you get

Clear control over who sees what and how people get in.

Original plan wording

Who Sees What: Roles & Permissions, Accounts and Sign-in — The permissions grid, Accounts & Roles, delegated account management, sign-up modes, and sign-in rules. Reader: admins and IT.

2.30

#### Knowing the System Is Healthy: Infrastructure, Alerts, Machines and Processing

Who it's for admins and IT staff

##### What it is

The pages that tell you whether Kite Pulse itself is healthy.

##### Why it matters

Admins need to know the system is working and hear when it is not.

##### How it works for you

- Automatic checks.
- A shared way of handling alerts.
- Thresholds (the levels that trigger an alert).
- Delivery history.
- The Machines, Data Collection, Processing and Server Storage pages.

##### What you get

A clear view of the system’s health, with alerts handled in one shared way.

Original plan wording

Knowing the System Is Healthy: Infrastructure, Alerts, Machines and Processing — Automatic checks, the shared alert workflow, thresholds, delivery history, Machines, Data Collection, Processing and Server Storage. Reader: admins and IT.

2.31

#### Data Rights: Export, Erase, Audit Log and Retention

Who it's for admins and data-protection officers

##### What it is

The tools for exporting and erasing data, the audit log, and how long data is kept.

##### Why it matters

Data-protection duties need a clear account of what is exported, what is erased, who did what, and how long things are kept.

##### How it works for you

- What export does and what erase does.
- An audit log (a record of actions taken) that cannot be edited.
- How long each kind of data is kept.

##### What you get

A clear picture of your data rights tools and a record nobody can change.

Optional Real deletion of session data is turned on by the server operator.

Original plan wording

Data Rights: Export, Erase, Audit Log and Retention — What export and erase do, the audit log that cannot be edited, and retention per kind of data. Reader: admins and data-protection officers. Optional parts: real deletion of session data is turned on by the server operator.

2.32

#### Leaked Credentials and Security Watch

Who it's for security teams and admins

##### What it is

A list of credentials (passwords and keys) found in AI conversations, plus a watch on other security risks.

##### Why it matters

Keys that turn up in AI conversations, sensitive changes nobody checked, and pasted secrets or personal data are risks the security team needs to know about.

##### How it works for you

- Keys found in AI conversations are shown masked, each with a status you can track.
- Sensitive changes that nobody checked.
- Secrets or personal data that were pasted in.
- Only counts and identifiers are shown.

##### What you get

A trackable list of leaked keys and a watch on security risks, without exposing the content itself.

Optional The list of found keys fills when the server operator runs a scan. Two tabs on this page need AI labelling to be switched on.

Original plan wording

Leaked Credentials and Security Watch — Masked keys found in AI conversations with a status to track, plus unchecked sensitive changes and pasted secrets or personal data, counts and identifiers only. Reader: security teams and admins. Optional parts: the list fills when the server operator runs a scan; the two tabs need AI labelling.

Category 3 of 13

## Use Cases and Real-World Applications

15 planned articles

Each article in this tab tells one concrete situation as a short story: who was involved, what happened, which Kite Pulse features they used, and what changed afterwards. All names and numbers in these stories are made up to illustrate the point. They are not results from real customers.

Read each entry as the outline of one story article. The title is the story’s name, and the parts below explain the situation, the features it shows and the outcome, in plain words.

3.1

#### The Stuck Agent Caught Before Lunch

Who it's for Team leads

##### What it is

A story about a team lead who spots a stuck AI agent, meaning an AI coding tool working through a task on its own. The lead finds it in The Office, Kite Pulse’s 3D view of the team, which has a meeting-room screen.

##### Why it matters

An agent that is stuck can quietly eat up a developer’s morning. The lead wants to catch it early without reading what people wrote to the AI.

##### How it works for you

- On The Office’s meeting-room screen, the lead sees one agent with its head down.
- The lead opens that agent’s desk and its “What the agent did” view.
- There the lead spots one command that keeps failing, again and again.
- The lead helps the developer, without reading the text of any messages.

##### What you get

The problem is sorted out before the morning is gone, and the developer’s message text stays unread.

Original plan wording

The Stuck Agent Caught Before Lunch — A lead sees one agent head down on The Office's meeting-room screen, opens its desk and “What the agent did”, spots the repeated failing command, and helps the developer before the morning is gone, without reading message text. Reader: team leads.

3.2

#### Moving the Migration to Monday: a Plan-Limit Save

Who it's for Team leads and engineering managers

##### What it is

A story about plan headroom: how much of their Claude plan limit each person has left. Claude is Anthropic’s AI assistant, and its plans have usage limits over set time windows, such as a week.

##### Why it matters

A large piece of work, such as a migration (a big planned change to a system), is risky to start when the people doing it are close to their Claude limit.

##### How it works for you

- Plan headroom shows two developers past 85% of their weekly Claude limit.
- Because of that, the large migration is moved to Monday.
- When a limit window does run out, a notice tells you when it resets.

##### What you get

Big work is planned around people’s limits, and when someone does run out, you know the time their limit comes back.

Optional The plan-limit figures cover Claude Code (Anthropic’s AI coding tool) only. Fresher figures need the background refresh, which an admin switches on.

Original plan wording

Moving the Migration to Monday: a Plan-Limit Save — Plan headroom shows two developers past 85% of their weekly Claude limit, so a large migration moves to Monday; when a window does run out, a notice gives the reset time. Reader: team leads and engineering managers. Optional parts: Claude Code only; fresher figures need the background refresh (admin switch).

3.3

#### The Test the AI Retried Six Times

Who it's for Developers

##### What it is

A story about a developer’s own scorecard in Kite Pulse, which points her to one thing going wrong in her work with the AI.

##### Why it matters

When the AI keeps retrying the same failing test command, the same failure repeats over and over.

##### How it works for you

- Her scorecard points at one test command that the AI retried six times.
- She fixes the test setup once.

##### What you get

Her failures drop.

Original plan wording

The Test the AI Retried Six Times — A developer's scorecard points at one test command retried six times; she fixes the setup once and her failures drop. Reader: developers.

3.4

#### One Build Error, Three Developers, Two Projects

Who it's for Engineering managers and platform teams (the people who look after shared tools and systems)

##### What it is

A story about the Work Problems page, which shows a build error (an error when the code is put together to run) that several people are hitting.

##### Why it matters

In the story, the same error is hitting three developers across two projects. Seen together, it can be handled once instead of three times.

##### How it works for you

- Work Problems shows that one build error is hitting three people.
- It is raised to the platform team as one fix.

##### What you get

One fix, raised once, for a problem three people shared.

Optional By default, only admins can see Work Problems.

Original plan wording

One Build Error, Three Developers, Two Projects — Work Problems shows one build error hitting three people, raised as one fix to the platform team. Reader: engineering managers and platform teams. Optional parts: admin-only by default.

3.5

#### “payments” and “payments-api” Were the Same Project

Who it's for Admins and project owners

##### What it is

A story about Duplicate Detection, which spots when one project shows up twice under different folder names.

##### Why it matters

Two folders, “payments” and “payments-api”, were really the same project. Split in two, the project did not show everyone who works on it.

##### How it works for you

- Duplicate Detection flags the two folders because they have the same repository address (the address where the project’s code is stored).
- The two are merged into one project.

##### What you get

One project that shows its four real contributors.

Original plan wording

“payments” and “payments-api” Were the Same Project — Duplicate Detection flags two folders with one repository address; merged, the project shows its four real contributors. Reader: admins and project owners.

3.6

#### The Shared Cursor Seat and the Budget at 80%

Who it's for Finance and budget holders

##### What it is

A story about finance spotting two money matters around AI tools: a shared Cursor account (Cursor is an AI coding editor; a seat is one paid user place on it) and a team close to its AI budget.

##### Why it matters

One Cursor account is being used by two people, and one team has already used 80% of its AI budget. Both need action before they become a problem.

##### How it works for you

- Finance finds a Cursor account used by two people.
- Finance also finds a team at 80% of its AI budget.
- Finance buys the seat and talks to the team.

##### What you get

Both are handled in time: the seat is bought and the team conversation happens while there is still budget left.

Original plan wording

The Shared Cursor Seat and the Budget at 80% — Finance finds a Cursor account used by two people and a team at 80% of its AI budget, buys the seat and talks to the team in time. Reader: finance and budget holders.

3.7

#### Before the Only Expert Moves Teams

Who it's for Engineering managers and admins

##### What it is

A story about capability ownership (who works on which part of the code) and the Tenure & Departure page (about people’s time in a team and their moves or departures).

##### Why it matters

Only one person edits a certain part of the code, and that person is about to move teams. Their knowledge could leave with them.

##### How it works for you

- Capability ownership shows a part that only one person edits.
- From Tenure & Departure, a knowledge-capture request is sent, asking for what that person knows to be handed over.

##### What you get

The hand-over is done before the person moves.

Optional Owned knowledge records (records of the knowledge a person holds) need AI labelling (labels that an AI model adds to sessions) to be switched on.

Original plan wording

Before the Only Expert Moves Teams — Capability ownership shows a part only one person edits; a knowledge-capture request from Tenure & Departure gets the hand-over done before the move. Reader: engineering managers and admins. Optional parts: owned knowledge records need AI labelling.

3.8

#### A New Joiner's First Afternoon with the Brain

Who it's for New joiners and their leads

##### What it is

A story about a new developer using the Brain (Kite Pulse’s Organizational Brain, its area for the team’s knowledge) on their first afternoon.

##### Why it matters

A new joiner needs to learn how things work and what colleagues have been doing, and wants to come to a colleague with one well-aimed question rather than many.

##### How it works for you

- The new developer uses the Graph (a picture of how things connect).
- They read the release SOP (the written step-by-step procedure for a release) in Documents.
- They ask a colleague’s agent about her recent work.
- Only then do they ask the colleague herself one sharp question.

##### What you get

By the end of the first afternoon, the new joiner has learned enough on their own to ask the colleague just one sharp question.

Optional The Brain must be on, which is an admin switch.

Original plan wording

A New Joiner's First Afternoon with the Brain — A new developer uses the Graph, reads the release SOP in Documents, and asks a colleague's agent about her recent work before asking her one sharp question. Reader: new joiners and their leads. Optional parts: Brain must be on (admin switch).

3.9

#### The Week of Work That Was Not Missing

Who it's for Developers

##### What it is

A story about a developer’s new project that Kite Pulse has found but is not yet sending to the team’s server.

##### Why it matters

A week of work looks as if it is missing from the record, because the new project is not syncing (not being sent up).

##### How it works for you

- The Workspace page shows a new project that was detected but is not syncing.
- The developer confirms the project in My Projects.

##### What you get

The work is on the record from that day, so the week of work is not missing.

Original plan wording

The Week of Work That Was Not Missing — Workspace shows a new project detected but not syncing; confirmed in My Projects, the work is on the record from that day. Reader: developers.

3.10

#### A Live Key in an AI Conversation

Who it's for Security and IT

##### What it is

A story about the Leaked Credentials page, where an admin finds a key (a secret code that gives access to a system) that someone pasted into an AI session. The key is shown masked, meaning hidden.

##### Why it matters

A live key, one that still works, has ended up inside an AI conversation. It needs to be followed up until it is dealt with.

##### How it works for you

- On Leaked Credentials, the admin finds the masked key pasted into an AI session.
- The admin tracks it until it is resolved.
- The admin also checks sensitive changes that nobody has checked yet.

##### What you get

The leaked key is followed through to resolution, and unchecked sensitive changes get looked at.

Optional The Leaked Credentials list fills when the server operator (the person who runs the Kite Pulse server) runs a scan. The Security watch tabs need AI labelling.

Original plan wording

A Live Key in an AI Conversation — An admin finds a masked key pasted into an AI session on Leaked Credentials, tracks it to resolution and checks unchecked sensitive changes. Reader: security and IT. Optional parts: the list fills when the server operator runs a scan; Security watch tabs need AI labelling.

3.11

#### The Friday Spreadsheet Nobody Builds Any More

Who it's for Executives and engineering managers

##### What it is

A story about scheduled company reports that arrive by email.

##### Why it matters

Someone used to build a spreadsheet by hand for leadership every Friday.

##### How it works for you

Leadership receives a scheduled company report by email instead of a hand-built spreadsheet.

##### What you get

Nobody builds the Friday spreadsheet any more; the report simply arrives.

Optional Admins set up the report schedules.

Original plan wording

The Friday Spreadsheet Nobody Builds Any More — Leadership receives a scheduled company report by email instead of a hand-built spreadsheet. Reader: executives and engineering managers. Optional parts: admins set up schedules.

3.12

#### Two People, One Service, One Stand-up

Who it's for Team leads

##### What it is

A story about the Team Overview and Collaboration pages showing two developers working in the same service (the same part of the software). A stand-up is a short regular team meeting.

##### Why it matters

Two people working separately in the same service can collide, getting in each other’s way.

##### How it works for you

- Team Overview and Collaboration show the two developers in the same service.
- The two are paired up to work together.

##### What you get

The two are paired before they collide.

Original plan wording

Two People, One Service, One Stand-up — Team Overview and Collaboration show two developers in the same service; they are paired before they collide. Reader: team leads.

3.13

#### From a Repeated Workflow to a Team Skill

Who it's for DevEx (developer experience) and platform teams

##### What it is

A story about Skill Candidates, which proposes a draft Claude Code skill. A skill is a saved set of steps that Claude Code (Anthropic’s AI coding tool) can reuse.

##### Why it matters

The team keeps doing the same workflow and re-typing the same steps each time.

##### How it works for you

- Skill Candidates spots the repeated workflow and proposes a draft Claude Code skill from it.
- The draft is approved.

##### What you get

The team stops re-typing the same steps.

Original plan wording

From a Repeated Workflow to a Team Skill — Skill Candidates proposes a draft Claude Code skill from a repeated workflow; approved, the team stops re-typing the same steps. Reader: DevEx and platform teams.

3.14

#### The Two-Hour Session That Went in Circles

Who it's for Developers

##### What it is

A story about a developer looking back at a two-hour AI session that kept going round in circles, using Playback (a replay of the session) and “What the agent did”.

##### Why it matters

Two hours went into a session that looped instead of moving forward.

##### How it works for you

- The developer replays the looping session with Playback and “What the agent did”.
- Next time, they write a clearer prompt (the instruction typed to the AI).

##### What you get

A clearer prompt for the next session, based on seeing where this one went in circles.

Original plan wording

The Two-Hour Session That Went in Circles — A developer replays a looping session with Playback and “What the agent did” and writes a clearer prompt next time. Reader: developers.

3.15

#### A Manager Who Asks Her Own Assistant

Who it's for Engineering managers

##### What it is

A story about a manager who connects Claude Code (Anthropic’s AI coding tool) to Kite Pulse with her own personal key, so she can ask it questions about the work Kite Pulse records.

##### Why it matters

She wants to know which projects had the most tool-call failures this month (times the AI tried to use a tool, such as running a command, and it failed), and to ask her own assistant rather than someone else.

##### How it works for you

- She connects Claude Code to Kite Pulse with her own key.
- She asks which projects had the most tool-call failures this month.
- The answer stays within her own view: only what she is allowed to see.

##### What you get

An answer to her question from her own assistant, limited to her own view.

Optional The server operator turns this on. Whether it runs in Chat mode or Direct access is an admin’s choice.

Original plan wording

A Manager Who Asks Her Own Assistant — A manager connects Claude Code to Kite Pulse with her own key and asks which projects had the most tool-call failures this month, answered within her own view. Reader: engineering managers. Optional parts: server operator turns it on; Chat mode or Direct access is an admin choice.

Category 4 of 13

## Benefits for Individual Developers

14 planned articles

This tab covers what a developer gets out of Kite Pulse for their own work and their own day. Each article tells the outcome from the developer’s seat. It is not a tour of the pages.

These are benefit articles: each one starts from something a single developer wants, such as credit for their work, fewer surprises or less reporting, and shows what Kite Pulse gives them. Page names appear only to show where the benefit comes from.

4.1

#### Never Lose Credit for Work You Did with AI

Who it's for Developers on a team that uses Kite Pulse.

##### What it is

Two pages that make sure your AI-assisted work is on the record: Workspace and My Projects.

##### Why it matters

When much of your work happens inside conversations with an AI tool, it can vanish from the record. Nobody sees it, so you may not get credit for it.

##### How it works for you

- Workspace shows you, project by project, that your work is detected, syncing (being sent to your team’s server) and processed.
- If something is missing, you fix it in My Projects.

##### What you get

Confidence that the work you did with AI counts and is visible, instead of disappearing.

Original plan wording

Never Lose Credit for Work You Did with AI — When much of your work happens inside AI conversations, it can vanish from the record; Workspace shows project by project that your work is detected, syncing and processed, and My Projects lets you fix anything missing. Reader: developers on a team that uses Kite Pulse.

4.2

#### Get Better Privately: a Top 3 to Try, with the Evidence

Who it's for Developers who want to sharpen how they work with AI.

##### What it is

My Scorecard, a page that gives you a short list (a top 3) of things worth changing in how you work with AI, so you can get better privately.

##### Why it matters

You want to know what to change and why, backed by evidence from your own work, not a guess.

##### How it works for you

Each item on the list comes with:

- a verdict,
- the reason,
- the evidence,
- what to try.

When there is too little to go on, it says “not enough data” rather than guessing.

##### What you get

A few concrete, evidence-backed changes to try, and an honest “not enough data” instead of a guess.

Original plan wording

Get Better Privately: a Top 3 to Try, with the Evidence — My Scorecard gives a short list of things worth changing, each with a verdict, the reason, the evidence and what to try, and says “not enough data” rather than guessing. Reader: developers who want to sharpen how they work with AI.

4.3

#### See Your Own Working Rhythm Clearly

Who it's for Developers curious about their own habits.

##### What it is

Facts about your work patterns and your working style, showing how you actually spend your time with AI.

##### Why it matters

How you think you work and how you actually work can differ. Seeing the real pattern is the first step to understanding your habits.

##### How it works for you

You see work-pattern facts such as:

- your peak hour,
- your busiest day,
- streaks,
- deep-focus sessions,
- parallel sessions (more than one at the same time),
- short bursts.

You also see your working style. Statistics about your prompts (the requests you type to the AI) are shown only to you.

##### What you get

A clear picture of your own working rhythm with AI, with your prompt statistics kept to yourself.

Original plan wording

See Your Own Working Rhythm Clearly — Work-pattern facts (peak hour, busiest day, streaks, deep-focus sessions, parallel sessions, short bursts) and your working style show how you actually spend time with AI; prompt statistics are shown only to you. Reader: developers curious about their own habits.

4.4

#### Stop Losing Half a Day to a Claude Plan Limit

Who it's for Developers on Claude plans.

##### What it is

A view of your own Claude plan usage, plus a notice when you hit a limit. A Claude plan allows a certain amount of use within a time window; when you use it up, you have to wait until it resets. This covers Claude Code plan limits only (Claude Code is Anthropic’s AI coding assistant), not other tools.

##### Why it matters

Running out of your plan in the middle of a long task can cost you half a day.

##### How it works for you

- Before a long task, you check your own Claude plan usage.
- The moment a window runs out, you get a notice that names that window and when it resets.

##### What you get

You can plan big tasks around your limits, and when one runs out you know right away when you can carry on.

Optional Fresher usage figures need the background plan refresh, which an admin switches on. Developers can opt out of it.

Original plan wording

Stop Losing Half a Day to a Claude Plan Limit — Check your own Claude plan usage before a long task, and get a notice naming the window and its reset time the moment one runs out. Claude Code plan limits only. Reader: developers on Claude plans. Optional parts: fresher figures need the background plan refresh (admin switch); developers can opt out.

4.5

#### Catch a Stuck Agent in Half an Hour, Not at the End of the Day

Who it's for Developers who leave agents running (an agent is an AI tool working through a task on its own).

##### What it is

A notice when an AI agent has been stuck, and a step-by-step view of what it did while stuck.

##### Why it matters

If you leave an agent running and it gets stuck, you may only find out at the end of the day.

##### How it works for you

- After 30 minutes stuck on the same problem, you get a notice that names the project.
- “What the agent did” shows you the stuck stretch, step by step.

##### What you get

You catch a stuck agent within half an hour, not at the end of the day, and can see the stuck stretch step by step.

Optional The server operator (whoever runs your team’s Kite Pulse server) can change the 30-minute interval or turn the notice off.

Original plan wording

Catch a Stuck Agent in Half an Hour, Not at the End of the Day — After 30 minutes stuck on the same problem you get a notice naming the project, and “What the agent did” shows the stuck stretch step by step. Reader: developers who leave agents running. Optional parts: the server operator can change the interval or turn it off.

4.6

#### Learn from the Session That Went in Circles

Who it's for Developers reviewing their own work.

##### What it is

Three ways to look back at a past AI session:

- Session Playback,
- the Session Summary, which is rule-based (built from fixed rules),
- “What the agent did”.

##### Why it matters

Sometimes a session goes wrong and goes in circles. Understanding why helps you avoid it next time.

##### How it works for you

You open a session that went wrong and look back through it with these views. Secrets (such as passwords or keys) stay masked throughout.

##### What you get

You learn what went wrong and write a better request to the AI next time.

Optional The Labels tab needs AI labelling (an optional feature that uses AI to add labels) to be on.

Original plan wording

Learn from the Session That Went in Circles — Session Playback, the rule-based Session Summary and “What the agent did” let you look back at a session that went wrong and write a better request next time; secrets stay masked. Reader: developers reviewing their own work. Optional parts: the Labels tab needs AI labelling.

4.7

#### Are You Checking What the AI Writes? A Private Verification Signal

Who it's for Developers who rely heavily on AI edits.

##### What it is

A private signal of how often you reviewed or tested what the AI produced.

##### Why it matters

Checking the AI’s work is a habit that is easy to let slip, especially when you rely on it heavily.

##### How it works for you

You see how often you reviewed or tested the AI’s output, with counts of the checks you made and the corrections you made.

##### What you get

An honest read on whether you are still checking what the AI writes.

Optional This needs AI labelling (an optional feature that uses AI to add labels) to be on.

Original plan wording

Are You Checking What the AI Writes? A Private Verification Signal — How often you reviewed or tested the AI's output, with counts of checks and corrections: an honest read on a habit that is easy to let slip. Reader: developers who rely heavily on AI edits. Optional parts: needs AI labelling.

4.8

#### One Place for All Your AI Work, Whichever Tool You Used

Who it's for Developers using more than one of the ten AI tools Kite Pulse supports.

##### What it is

One timeline that brings together your work from different AI tools.

##### Why it matters

If you switch between tools, for example Claude Code in the morning and Cursor (an AI code editor) in the afternoon, your work is split across them.

##### How it works for you

Work from each tool lands in the same timeline, under the right project. You can filter it by:

- tool,
- model (the AI model used),
- session type.

##### What you get

All your AI work in one place, whichever tool you used.

Original plan wording

One Place for All Your AI Work, Whichever Tool You Used — Claude Code in the morning and Cursor in the afternoon still land in one timeline under the right project, filtered by tool, model or session type. Reader: developers using more than one of the ten supported tools.

4.9

#### End the Day Knowing What You Left Open

Who it's for Developers juggling several threads of work.

##### What it is

My Day, a page that lays out your day. Only you can see it.

##### Why it matters

When you juggle several threads, it is easy to lose track of what is still unfinished.

##### How it works for you

My Day shows:

- what you worked on,
- what you started,
- what you finished,
- what you left open,
- where you got stuck,
- what you learned.

##### What you get

You end the day knowing what you left open, in a view that is visible only to you.

Optional This needs AI labelling (an optional feature that uses AI to add labels) to be on.

Original plan wording

End the Day Knowing What You Left Open — My Day lays out what you worked on, started, finished and left open, where you got stuck and what you learned, visible only to you. Reader: developers juggling several threads. Optional parts: needs AI labelling.

4.10

#### No Timesheets, No Status Updates

Who it's for Developers tired of status rituals (timesheets, status updates and similar reporting).

##### What it is

Kite Pulse captures your work in the background and shows it to the team, so you do not have to report it yourself.

##### Why it matters

Time spent filling in timesheets and writing status updates is time not spent doing the work.

##### How it works for you

- Capture runs in the background while you work.
- The Office (Kite Pulse’s 3D view of the team) and Team Overview show your work in motion.

##### What you get

Less time reporting and more time doing.

Original plan wording

No Timesheets, No Status Updates — Capture runs in the background, and The Office and Team Overview show your work in motion, so you spend less time reporting and more time doing. Reader: developers tired of status rituals.

4.11

#### You Stay in Control of What Is Collected

Who it's for Developers wary of workplace monitoring.

##### What it is

The controls that keep you in charge of what Kite Pulse collects about you.

##### Why it matters

A tool that looks at your work can feel like workplace monitoring. You want to know, and decide, what is collected.

##### How it works for you

- You choose which projects sync.
- Nothing is sent before you confirm.
- Secrets (such as passwords or keys) are masked twice.
- The Privacy page shows every data point about you and who can see it.

##### What you get

Control over what is collected and a full view of what is held about you and who can see it.

Optional The “Who asked my agent” part needs the Brain (Kite Pulse’s team-knowledge area, also called the Organizational Brain) to be on, which an admin switches on.

Original plan wording

You Stay in Control of What Is Collected — You choose which projects sync, nothing is sent before you confirm, secrets are masked twice, and the Privacy page shows every data point about you and who can see it. Reader: developers wary of workplace monitoring. Optional parts: “Who asked my agent” needs the Brain on (admin switch).

4.12

#### Get Up to Speed on a New Project Without a Week of Asking Around

Who it's for Developers joining a project or a team.

##### What it is

Parts of the Brain (Kite Pulse’s Organizational Brain, an optional area that brings together who works on what, the team’s written procedures and teammates’ recent work) that help you learn a new project quickly: the Graph, Documents, and asking a teammate’s agent.

##### Why it matters

Joining a new project can mean a week of asking people around you who does what and how things are done.

##### How it works for you

- The Brain’s Graph shows who works on what.
- Documents holds the team’s SOPs (standard operating procedures: the written “how we do it” steps).
- Asking a teammate’s agent shows you their recent synced work.

##### What you get

You get up to speed on your own, so the one question you do ask a teammate is a sharp one.

Optional The Brain must be on, which an admin switches on.

Original plan wording

Get Up to Speed on a New Project Without a Week of Asking Around — The Brain's Graph shows who works on what, Documents holds the team's SOPs, and asking a teammate's agent shows their recent synced work, so your one question to them is a sharp one. Reader: developers joining a project or team. Optional parts: Brain must be on (admin switch).

4.13

#### Stay on a Current Claude Code Without Watching Release Notes

Who it's for Developers using Claude Code.

##### What it is

A “Claude Code out of date” notice.

##### Why it matters

Keeping Claude Code current would otherwise mean watching its release notes yourself.

##### How it works for you

- The notice tells you when your version of Claude Code is behind the stable release.
- It clears once you update.

##### What you get

You stay on a current Claude Code without having to watch release notes.

Original plan wording

Stay on a Current Claude Code Without Watching Release Notes — A “Claude Code out of date” notice tells you when your build is behind the stable release and clears once you update. Reader: developers using Claude Code.

4.14

#### Personal Insight on Your Own Laptop, with Nobody Else's Server

Who it's for Freelancers and solo developers.

##### What it is

Kite Pulse running entirely on one computer, for one person.

##### Why it matters

If you work alone, you may have no team server, and you may not want to use a vendor’s cloud or anyone else’s server.

##### How it works for you

You run Kite Pulse on your own computer. You get the same personal pages, and there is no vendor cloud involved.

##### What you get

Personal insight into your own work on your own laptop, with nobody else’s server.

Original plan wording

Personal Insight on Your Own Laptop, with Nobody Else's Server — Kite Pulse runs entirely on one computer for one person, with the same personal pages and no vendor cloud. Reader: freelancers and solo developers.

Category 5 of 13

## Benefits for Development Teams and Managers

13 planned articles

This tab is about results for three groups: team leads, engineering managers, and the people inside engineering who look after the budget. The results are teams that run better, a fairer reading of the work people do, and spending that stays on plan.

These articles describe outcomes for managers, not how each feature is built. Each one names the Kite Pulse pages a manager would use, what they show, and which parts are optional.

5.1

#### Stand-ups That Start from Facts, Not Round-the-Room Updates

Who it's for Team leads

##### What it is

Two Kite Pulse pages, Team Overview and The Office (Kite Pulse’s 3D view of the team), show the state of each person before the stand-up (a short regular team meeting) starts.

##### Why it matters

In many stand-ups, time goes on going round the room so each person can give an update. That leaves less time for fixing what is actually wrong.

##### How it works for you

Before the meeting, you open Team Overview or The Office and see who is:

- online
- coding
- stuck
- in need of attention

##### What you get

You walk in already knowing the facts, so the stand-up can go to solving problems.

Original plan wording

Stand-ups That Start from Facts, Not Round-the-Room Updates — Team Overview and The Office show who is online, coding, stuck or needs attention before the meeting starts, so the stand-up goes to solving problems. Reader: team leads.

5.2

#### Help a Stuck Developer Without Reading Their Conversation

Who it's for Team leads and engineering managers

##### What it is

When a developer's AI agent (the AI coding tool doing a task for them) gets stuck, the manager gets the same “AI agent stuck” notice as the developer. A view called “What the agent did” then shows what happened.

##### Why it matters

You want to help someone who is stuck, but without reading their conversation with the AI.

##### How it works for you

You receive the “AI agent stuck” notice. You open “What the agent did”, which shows:

- the tools the agent used
- the commands it ran
- the errors it hit
- the stretch of time where it was stuck

It shows no message text.

##### What you get

You can see where the work went wrong and help the developer, without seeing what anyone wrote.

Original plan wording

Help a Stuck Developer Without Reading Their Conversation — The manager gets the same “AI agent stuck” notice, and “What the agent did” shows tools, commands, errors and the stuck stretch with no message text. Reader: team leads and engineering managers.

5.3

#### Plan Sprints Around Real Limits

Who it's for Engineering managers

##### What it is

Two views help you plan a sprint (a short, fixed period of planned work) around Claude plan limits, the usage caps on a person's Claude subscription. Plan headroom shows who is close to a limit. The plan usage report shows past peaks. This covers Claude Code (Anthropic's AI coding tool) only.

##### Why it matters

If someone hits their plan limit in the middle of heavy work, that work stalls.

##### How it works for you

- Plan headroom lists who is near a Claude plan limit, with the person closest to the limit first.
- The plan usage report shows the past peaks in usage.

##### What you get

You can move heavy work before it stalls.

Optional Downloading the plan usage report is limited to admins unless that setting is changed.

Original plan wording

Plan Sprints Around Real Limits — Plan headroom shows who is near a Claude plan limit, worst first, and the plan usage report shows past peaks, so heavy work moves before it stalls. Claude Code only. Reader: engineering managers. Optional parts: downloading the report is admin-only by default.

5.4

#### Read Activity Fairly: Leave, On-Call and Team Moves

Who it's for Engineering managers and team leads

##### What it is

Three things help you read people's activity fairly: the Leave & On-Call page, team membership that is recorded with dates, and insights that admit when there is too little data.

##### Why it matters

Activity numbers can mislead. A person on holiday can look disengaged, history can be wrong when people move between teams, and an insight built on too little data is a guess.

##### How it works for you

- Leave & On-Call records leave and on-call duty (being the person who responds to problems), so a holiday does not look like disengagement.
- Team membership has dates, so when people move teams, past history stays accurate.
- Insights say “not enough data” instead of guessing.

##### What you get

A fair, accurate picture of each person's activity, without false conclusions.

Original plan wording

Read Activity Fairly: Leave, On-Call and Team Moves — Leave & On-Call keeps a holiday from looking like disengagement, dated team membership keeps history accurate, and insights say “not enough data” rather than guess. Reader: engineering managers and team leads.

5.5

#### Fix the System, Not the Person

Who it's for Team leads and platform owners

##### What it is

Two pages point at problems in how work is set up rather than at people: Work Problems and the Blocker Board.

##### Why it matters

Lost time often has causes that come back again and again. Fixing those causes helps everyone, and it does not need anyone to be blamed.

##### How it works for you

- Work Problems groups together commands that fail and repeated retries, and suggests actions to take.
- The Blocker Board turns the causes of lost time that keep coming back into cards. The cards never name a person.

##### What you get

A list of things to fix in the system, with suggested actions, and no finger-pointing at individuals.

Optional This is admin-only by default: only admins see it unless that setting is changed. The Blocker Board also needs AI labelling (an optional feature that uses an AI model to label the work) and suggestion rules (the rules that produce its suggestions) to be switched on.

Original plan wording

Fix the System, Not the Person — Work Problems groups failing commands and retries with suggested actions, and the Blocker Board turns recurring causes of lost time into cards that never name a person. Reader: team leads and platform owners. Optional parts: admin-only by default; the Blocker Board needs AI labelling and suggestion rules switched on.

5.6

#### Stop Two People Building the Same Thing

Who it's for Team leads

##### What it is

The Collaboration page and each project's page help you spot when people overlap, including when two people are building the same thing.

##### Why it matters

When two people build the same thing without knowing it, one person's effort is wasted.

##### How it works for you

- Collaboration shows which projects several people are working in, and how much each person spent there.
- The project page flags duplicate work.

##### What you get

You can see the overlap and step in before the same thing gets built twice.

Optional The duplicate-work flag needs AI labelling to be switched on.

Original plan wording

Stop Two People Building the Same Thing — Collaboration shows which projects several people are in and how much each spent there, and the project page flags duplicate work. Reader: team leads. Optional parts: duplicate work needs AI labelling.

5.7

#### Know Which Projects Are Alive Without Chasing Anyone

Who it's for Engineering managers

##### What it is

The All Projects page shows the state of every project, and Duplicate Detection makes sure each repository (the place a project's code is kept) is counted only once.

##### Why it matters

Without this, finding out which projects are still alive means chasing people to ask.

##### How it works for you

All Projects shows each project as active, stable or dormant (inactive), along with its:

- contributors
- sessions
- last activity
- open blockers

Duplicate Detection keeps one repository from being counted twice.

##### What you get

An accurate view of which projects are alive, without asking anyone.

Optional The figures for project phase, risk and blockers need AI labelling to be switched on.

Original plan wording

Know Which Projects Are Alive Without Chasing Anyone — All Projects shows each project as active, stable or dormant, with contributors, sessions, last activity and open blockers, and Duplicate Detection keeps one repository from being counted twice. Reader: engineering managers. Optional parts: phase, risk and blocker figures need AI labelling.

5.8

#### Is the Team's Work with AI Getting Better?

Who it's for Engineering managers

##### What it is

Three pages, Trends, Team Review and AI Collaboration, show how the team's work with AI changes over time.

##### Why it matters

You want to know whether the team's work with AI is getting better.

##### How it works for you

These pages show, over weeks and months:

- completion (how much work gets finished)
- friction (where work gets hard or slows down)
- changes that were checked

The figures are pooled for the team and never shown per person.

##### What you get

A team-level answer to whether things are improving, without singling anyone out.

Optional These pages need AI labelling to be switched on. Team Review and AI Collaboration are for admins only unless that setting is changed.

Original plan wording

Is the Team's Work with AI Getting Better? — Trends, Team Review and AI Collaboration show completion, friction and checked changes over weeks and months, pooled and never per person. Reader: engineering managers. Optional parts: need AI labelling; Team Review and AI Collaboration are admin-only by default.

5.9

#### Better One-to-Ones from the Same Report the Developer Sees

Who it's for Engineering managers

##### What it is

Each developer has a page that shows the same report the developer sees for themselves.

##### Why it matters

A one-to-one meeting goes better when the manager and the developer are looking at the same facts.

##### How it works for you

You open the developer's page and see the report that person sees, without their private fields.

##### What you get

Your one-to-one starts from facts you both share.

Original plan wording

Better One-to-Ones from the Same Report the Developer Sees — A developer's page shows the report that person sees, without private fields, so a one-to-one starts from shared facts. Reader: engineering managers.

5.10

#### Keep the Team's AI Budget on Plan

Who it's for Engineering budget holders

##### What it is

Monthly budgets for each team or project, plus a token pace line. A token is a small piece of text the AI reads or writes; AI tools charge by tokens.

##### Why it matters

You need the team's AI spending to stay on plan.

##### How it works for you

- A monthly budget is set for a team or a project, and you get an alert when spending reaches 80% of it and again at 100%.
- The token pace line shows where usage is heading over the next 30 days.

##### What you get

Early warning, so you can keep the AI budget on plan.

Optional Budgets are set by admins.

Original plan wording

Keep the Team's AI Budget on Plan — Monthly budgets per team or project alert at 80% and 100%, and the token pace line shows where usage is heading over the next 30 days. Reader: engineering budget holders. Optional parts: budgets are set by admins.

5.11

#### Spot the One-Person Parts of Your Product Before They Hurt

Who it's for Engineering managers and tech leads

##### What it is

Capability ownership shows who works on each capability (each part of your product). It does not use an AI model.

##### Why it matters

Some parts of a product depend on just one person. That hurts if that person is away or leaves.

##### How it works for you

For each capability, you see:

- who edits it and who reads it
- each person's share
- the bus factor (how many people would need to be gone before nobody knows that part)
- a hint about handing the work over

##### What you get

You find the one-person parts of your product before they cause trouble, with a pointer on how to hand them over.

Optional Capability ownership is for admins only unless that setting is changed.

Original plan wording

Spot the One-Person Parts of Your Product Before They Hurt — Capability ownership shows who edits and reads each capability, each person's share and the bus factor, with a hand-over hint. No AI model. Reader: engineering managers and tech leads. Optional parts: admin-only by default.

5.12

#### Report Upward Without Building a Spreadsheet

Who it's for Managers who report to leadership

##### What it is

The company report, and scheduled reports that send it by email.

##### Why it matters

Reporting to leadership often means building a spreadsheet by hand.

##### How it works for you

- The company report compares any period you choose with the period before it.
- Scheduled reports email the company report daily, weekly or monthly.

##### What you get

A ready report for leadership, without building a spreadsheet.

Optional Downloading the report and setting up schedules are for admins unless that setting is changed.

Original plan wording

Report Upward Without Building a Spreadsheet — The company report compares any period with the one before, and scheduled reports email it daily, weekly or monthly. Reader: managers reporting to leadership. Optional parts: downloads and schedules are admin by default.

5.13

#### Invest in the Tooling Your Team Actually Uses

Who it's for Developer-experience leads and platform leads

##### What it is

Three pages, Models, Agent features and Agent Setup, show which AI tooling the team relies on. A fourth, Skill Candidates, turns work the team repeats into draft skills (saved instructions an AI coding tool can reuse).

##### Why it matters

You want to put your investment into the tooling your team actually uses.

##### How it works for you

Models, Agent features and Agent Setup show which of these the team relies on:

- AI models
- Claude Code features
- skills
- MCP servers (add-ons that connect an AI tool to other tools and data)

Skill Candidates takes workflows the team repeats and turns them into draft skills.

##### What you get

A clear view of the tools in real use, plus draft skills built from your team's own repeated work.

Optional Agent Setup needs its own optional data collection (an optional read), which an admin switches on.

Original plan wording

Invest in the Tooling Your Team Actually Uses — Models, Agent features and Agent Setup show which models, Claude Code features, skills and MCP servers the team relies on, and Skill Candidates turns repeated workflows into draft skills. Reader: developer-experience and platform leads. Optional parts: Agent Setup needs its optional read (admin switch).

Category 6 of 13

## Benefits for Organizations

14 planned articles

This tab is about what Kite Pulse gives the company as a whole. It covers five groups: leadership, company finance, HR and people teams, security and IT, and the organisation’s culture and knowledge.

Each article describes an outcome for one of these audiences, not how a feature works. Read the “Who it’s for” line first to find the articles meant for you.

6.1

#### Decisions Based on What Happened, Not on Self-Reports

Who it’s for Executives and engineering leadership.

##### What it is

Three views for leaders: Organisation Overview, the company report and Trends. Their figures come from the sessions themselves. A session is the record of work that an AI coding tool already keeps.

##### Why it matters

Surveys and estimates rely on what people say happened. Leaders need decisions based on what actually happened.

##### How it works for you

You open Organisation Overview, the company report or Trends. What you see is drawn from the real sessions, not from surveys or estimates.

##### What you get

You can make decisions on what really happened instead of on self-reports.

Optional The Trends measures that are based on labels work only when AI labelling is on. AI labelling is an optional feature in which an AI service labels the sessions.

Original plan wording

Decisions Based on What Happened, Not on Self-Reports — Organisation Overview, the company report and Trends draw on the sessions themselves rather than surveys or estimates. Reader: executives and engineering leadership. Optional parts: Trends label measures need AI labelling.

6.2

#### One Set of Figures Everyone Agrees On

Who it’s for Leadership, and anyone who has sat through an argument about whose numbers are right.

##### What it is

Every page in Kite Pulse reads the same sessions. So these never contradict each other:

- The Office (a Kite Pulse page with a 3D view)
- team pages
- usage
- project health

##### Why it matters

When different reports give different numbers, meetings turn into disputes about the numbers.

##### How it works for you

Whichever of these pages you open, the figures come from the same sessions, so they match.

##### What you get

One set of figures that everyone can agree on.

Original plan wording

One Set of Figures Everyone Agrees On — Every page reads the same sessions, so The Office, team pages, usage and project health never contradict each other. Reader: leadership and anyone who has sat through a numbers dispute.

6.3

#### Turn the One-Line AI Bill into a Breakdown

Who it’s for Company finance.

##### What it is

A breakdown of token use, with an estimated cost for each tool. A token is a small piece of text the AI reads or writes, and AI tools charge by tokens. You can split token use by:

- person
- project
- tool
- model (the AI behind a tool)
- period

##### Why it matters

The AI bill can arrive as one line. Finance needs to see where the AI money goes.

##### How it works for you

You look at token use split in the ways above, next to an estimated cost for each tool. These costs are labelled “not billed spend”. They are estimates, not the amount on the invoice.

##### What you get

A view of where the company’s AI money goes.

Original plan wording

Turn the One-Line AI Bill into a Breakdown — Token use by person, project, tool, model and period, with an estimated cost per tool, gives finance a view of where AI money goes. Labelled “not billed spend”. Reader: company finance.

6.4

#### Find Shared, Personal and Idle Seats

Who it’s for Finance and procurement.

##### What it is

The Tool Accounts page. It covers these AI coding tools: Claude Code, Codex, Cursor, OpenCode and GitHub Copilot. A “seat” is a paid account for one user of a tool.

##### Why it matters

You need to know which seats are shared, which work is done on personal accounts, and which seats sit idle.

##### How it works for you

- Tool Accounts marks accounts that several people share.
- It shows personal accounts that are being used for work.
- It puts each seat’s price beside its usage, so you can spot idle seats.

##### What you get

You can find shared, personal and idle seats across these five tools.

Original plan wording

Find Shared, Personal and Idle Seats — Tool Accounts marks shared accounts and reveals personal accounts used for work, and seat prices sit beside usage. Covers Claude Code, Codex, Cursor, OpenCode and GitHub Copilot. Reader: finance and procurement.

6.5

#### See Real AI Adoption Across the Company

Who it’s for Executives and technology leaders.

##### What it is

A view of how the company really uses AI. A model is the AI behind a tool. It shows:

- which AI tools and models are actually used
- how that changes over time
- which models each project relies on

##### Why it matters

Leaders need to see real AI adoption, not just which tools have been bought.

##### How it works for you

You see the tools and models in use, how their use changes over time, and which models each project depends on.

##### What you get

A picture of real AI adoption across the company.

Original plan wording

See Real AI Adoption Across the Company — Which AI tools and models are actually used, how that changes over time and which models each project relies on. Reader: executives and technology leaders.

6.6

#### A Measurement Culture That Describes Work Instead of Ranking People

Who it’s for HR, people teams and works councils (bodies that represent employees).

##### What it is

A way of measuring that describes the work rather than ranking the people who do it.

##### Why it matters

Measurement should describe work, not rank people.

##### How it works for you

- Team views never single out one person.
- Measures that pool a team’s figures together are held back for small teams.
- The Insights Catalog says who is allowed to see each insight.

##### What you get

A measurement culture that describes the work instead of ranking people.

Original plan wording

A Measurement Culture That Describes Work Instead of Ranking People — Team views never single out a person, pooled measures hold back small teams, and the Insights Catalog says who may see each insight. Reader: HR, people teams and works councils.

6.7

#### Developer Buy-in Through Visible Privacy

Who it’s for HR, works councils (bodies that represent employees) and leaders planning a rollout.

##### What it is

Privacy protections that developers can see for themselves.

##### Why it matters

Developers have to accept the tool. When they do, the figures stay complete.

##### How it works for you

- Each person consents before their data is synced (sent to the server).
- No keystrokes, screenshots or source files are read.
- Secrets are masked twice.
- Each person has their own Privacy page.

##### What you get

A tool developers accept, which keeps the figures complete.

Original plan wording

Developer Buy-in Through Visible Privacy — Consent before sync, no keystrokes, screenshots or source files read, secrets masked twice and a Privacy page per person make a tool developers accept, which keeps the figures complete. Reader: HR, works councils and leaders planning a rollout.

6.8

#### Keep What the Organisation Learns

Who it’s for Leadership and knowledge owners.

##### What it is

Three ways to keep knowledge: knowledge records, the Capability Map and draft skills (saved, reusable instructions for an AI coding tool). There is also the optional Brain (the Organizational Brain), where people can explore that knowledge.

##### Why it matters

When one person discovers something, the organisation should keep it for the next person.

##### How it works for you

Knowledge records, the Capability Map and draft skills hold on to what one person found. If the Brain is on, anyone can explore that knowledge, within their own access.

##### What you get

One person’s discovery is kept for the next person.

Optional Knowledge records need AI labelling (an optional feature in which an AI service labels the sessions). The Brain must be on, and an admin turns it on with a switch.

Original plan wording

Keep What the Organisation Learns — Knowledge records, the Capability Map and draft skills keep one person’s discovery for the next, and the optional Brain lets anyone explore it within their own access. Reader: leadership and knowledge owners. Optional parts: knowledge records need AI labelling; the Brain must be on (admin switch).

6.9

#### When Someone Leaves, Their Know-how Does Not

Who it’s for HR, and managers planning a hand-over.

##### What it is

Two tools for when someone leaves: the departure report and capture requests.

##### Why it matters

When a person leaves, their know-how should not leave with them.

##### How it works for you

- The departure report lists the capabilities at risk, the records the person owns, and the files only they edited.
- Capture requests ask the person to write their knowledge down before they go.

##### What you get

A hand-over where the person’s know-how stays with the organisation.

Optional This is admin-only by default.

Original plan wording

When Someone Leaves, Their Know-how Does Not — The departure report lists capabilities at risk, records owned and files only they edited, and capture requests ask the person to write knowledge down before they go. Reader: HR and managers planning a hand-over. Optional parts: admin-only by default.

6.10

#### Catch Leaked Credentials and Pasted Personal Data

Who it’s for Security teams.

##### What it is

Two views: Leaked Credentials and Security watch. A credential is a key, password or similar secret that gives access to a system.

##### Why it matters

People sometimes paste credentials or personal data into AI conversations, and security teams need to catch it.

##### How it works for you

- Leaked Credentials tracks keys found in AI conversations. The keys are shown masked.
- Security watch lists prompts (messages to the AI) where someone pasted a secret or personal data. It shows only counts and identifiers (references to where it happened), not the pasted content.

##### What you get

You can catch leaked credentials and pasted personal data.

Optional The main list fills when the server operator (the person who runs your Kite Pulse server) runs a scan. Security watch needs AI labelling (an optional feature in which an AI service labels the sessions).

Original plan wording

Catch Leaked Credentials and Pasted Personal Data — Leaked Credentials tracks masked keys found in AI conversations, and Security watch lists prompts where someone pasted a secret or personal data, counts and identifiers only. Reader: security teams. Optional parts: the main list fills when the server operator runs a scan; Security watch needs AI labelling.

6.11

#### Your Data Stays on Infrastructure You Control

Who it’s for IT and security decision-makers.

##### What it is

Kite Pulse runs on your own computer, your own network or your own cloud account. There is no vendor cloud in between.

##### Why it matters

You decide where your data is kept. This is called data residency.

##### How it works for you

You choose where to run Kite Pulse: your own computer, network or cloud account. Your data stays there.

##### What you get

Your data stays on infrastructure you control, and where it lives is your choice.

Original plan wording

Your Data Stays on Infrastructure You Control — Kite Pulse runs on your own computer, network or cloud account with no vendor cloud in between, so data residency is your choice. Reader: IT and security decision-makers.

6.12

#### Clear Accountability for Who Sees What

Who it’s for IT, security and data-protection officers.

##### What it is

Controls that make it clear who can see what, and what happens to the data.

##### Why it matters

You need clear accountability for who sees what.

##### How it works for you

- A permissions grid sets, page by page, who can see each page.
- An audit log records what happened, and it cannot be edited.
- Retention (how long data is kept) is set for each kind of data.
- On request, one person’s data can be exported or erased (see the note below about session data).

##### What you get

Clear accountability for who sees what.

Optional The server operator (the person who runs your Kite Pulse server) turns on real deletion of session data.

Original plan wording

Clear Accountability for Who Sees What — A per-page permissions grid, an audit log that cannot be edited, retention per kind of data, and export or erasure of one person’s data on request. Reader: IT, security and data-protection officers. Optional parts: real deletion of session data is turned on by the server operator.

6.13

#### Know the System Is Healthy Before Users Tell You

Who it’s for IT and platform administrators.

##### What it is

Automatic checks that raise alerts when something goes wrong. The alerts go on one shared alert list.

##### Why it matters

You want to know the system is healthy before users have to tell you it is not.

##### How it works for you

The checks raise an alert for:

- processing that has stalled
- low memory or low disk space
- silent collectors (a collector is the program that picks up the AI tools’ session history)
- failed sign-ins

##### What you get

You learn about problems before users tell you, in one shared alert list.

Optional Email alerts need the server operator (the person who runs your Kite Pulse server) to set up mail. Alerts in Slack (a team chat app) are turned on by an admin with a switch.

Original plan wording

Know the System Is Healthy Before Users Tell You — Automatic checks raise alerts for stalled processing, low memory or disk, silent collectors and failed sign-ins, on one shared alert list. Reader: IT and platform administrators. Optional parts: email needs the operator to set up mail; Slack alerts are an admin switch.

6.14

#### Adopt AI Analysis at a Pace You Control

Who it’s for Security, procurement and leadership.

##### What it is

Everything core in Kite Pulse works without any AI service. Each AI feature is opt-in.

##### Why it matters

You want to adopt AI analysis at your own pace, without an open-ended bill.

##### How it works for you

- Nothing AI-based runs unless you opt in to it.
- Each AI feature has its own monthly cap, which keeps its bill from being open-ended.
- Each AI feature needs an admin’s approval.

##### What you get

AI analysis at a pace you control, with no open-ended bill.

Optional AI labelling needs a key (an access key for the AI service) that an admin enters on the Classification page. Brain Chat needs a key from the server operator (the person who runs your Kite Pulse server).

Original plan wording

Adopt AI Analysis at a Pace You Control — Everything core works with no AI service, and each AI feature is opt-in with its own monthly cap and admin approval, so there is no open-ended bill. Reader: security, procurement and leadership. Optional parts: AI labelling needs a key an admin enters on Classification; Brain Chat needs a key from the server operator.

Category 7 of 13

## Problems the Product Solves

16 planned articles

These articles put the problem first. Each one starts from a single problem teams have today. It explains why that problem exists now that work is done with AI assistants. Then it shows how Kite Pulse deals with it.

Read each entry as “here is a pain you may recognise, here is why it happens, here is what Kite Pulse does about it.” Each entry also names who the article is written for.

7.1

#### The Work Moved into AI Conversations, and Your Visibility Did Not Follow

Who it's for Engineering leaders who are meeting this problem for the first time.

##### What it is

An article about a gap: much of the real work now happens inside conversations with AI tools, but the usual ways of seeing work have not caught up.

##### Why it matters

Commits (saved changes to code), pull requests (requests to add a change to the shared code) and tickets (tracked tasks) only show what came out at the end. They do not show how the work got done.

##### How it works for you

Kite Pulse reads the AI sessions themselves, with the person’s consent.

##### What you get

You can see the process behind the work, not just the end result.

Original plan wording

The Work Moved into AI Conversations, and Your Visibility Did Not Follow — Commits, pull requests and tickets show only what came out the other end; Kite Pulse reads the AI sessions themselves, with consent, to show the process. Reader: engineering leaders meeting the problem for the first time.

7.2

#### More Commits, Same Delivery Speed: Where Did the Time Go?

Who it's for Engineering managers and leadership.

##### What it is

An article about why a team can produce more commits (saved code changes) without delivering any faster.

##### Why it matters

Inside AI sessions, people retry and hit dead ends. Counting outputs, such as commits, cannot show this lost time.

##### How it works for you

Kite Pulse measures:

- active time
- sessions
- retries
- stuck stretches

##### What you get

You can see where the time went, including the retries and stuck periods that output counts hide.

Original plan wording

More Commits, Same Delivery Speed: Where Did the Time Go? — Retries and dead ends inside AI sessions are invisible to output counts; Kite Pulse measures active time, sessions, retries and stuck stretches. Reader: engineering managers and leadership.

7.3

#### The AI Bill Nobody Can Break Down

Who it's for Finance and budget holders.

##### What it is

An article about AI spending that arrives as one lump that no one can split up.

##### Why it matters

Several tools, several subscriptions and shared accounts all end up as one unclear line on the bill.

##### How it works for you

Kite Pulse shows:

- token use (a token is a small piece of text the AI reads or writes; AI tools charge by tokens) by person, by project, by tool and by model
- estimated cost for each tool
- shared accounts
- budgets

##### What you get

You can break the AI bill down by who used it, on what, with which tool and model, and see estimated cost per tool, shared accounts and budgets.

Original plan wording

The AI Bill Nobody Can Break Down — Several tools, subscriptions and shared accounts become one opaque line; Kite Pulse shows token use by person, project, tool and model, estimated cost per tool, shared accounts and budgets. Reader: finance and budget holders.

7.4

#### The Plan Limit That Ends Your Afternoon

Who it's for Developers and leads who are on Claude plans.

##### What it is

An article about Claude plan limits: a Claude subscription allows a certain amount of use in a time window, and once that is used up you have to wait for it to reset. This applies to Claude Code (Anthropic’s AI coding assistant) only.

##### Why it matters

Developers only find out that a Claude plan window is used up when their work suddenly stops.

##### How it works for you

Kite Pulse shows how close each person is to their limit. It sends a notice that includes the reset time.

##### What you get

You know ahead of time how close you are and when the window resets, instead of being stopped by surprise. This covers Claude Code only.

Original plan wording

The Plan Limit That Ends Your Afternoon — Developers find out a Claude plan window is used up only when work stops; Kite Pulse shows how close each person is and sends a notice with the reset time. Claude Code only. Reader: developers and leads on Claude plans.

7.5

#### Ten AI Tools, Ten Histories, No Single Picture

Who it's for Teams that use a mix of AI tools.

##### What it is

An article about pulling the history of many different AI tools into one place.

##### Why it matters

Each AI tool keeps its own records, in its own format, so there is no single picture of the work.

##### How it works for you

Kite Pulse brings ten tools together into one timeline. If the same repository (a project’s shared code folder) is on two laptops, it is counted as one project, not two.

##### What you get

One timeline across ten tools, with each project counted once.

Original plan wording

Ten AI Tools, Ten Histories, No Single Picture — Each tool keeps its own records in its own format; Kite Pulse brings ten tools into one timeline, with one repository on two laptops counted as one project. Reader: teams using a mix of AI tools.

7.6

#### The Agent That Sat Stuck While You Were in a Meeting

Who it's for Developers and team leads.

##### What it is

An article about AI agents (AI tools that carry out tasks on their own) that get stuck while nobody is watching.

##### Why it matters

Agents now run without anyone watching them, and they can go round in circles for hours.

##### How it works for you

- Kite Pulse notices when an agent has been stuck for 30 minutes.
- It tells the person and their manager.
- It shows the stretch of time the agent was stuck.

##### What you get

A stuck agent is caught after 30 minutes instead of wasting hours, and you can see exactly where it was stuck.

Original plan wording

The Agent That Sat Stuck While You Were in a Meeting — Agents now run unattended and can loop for hours; Kite Pulse notices after 30 minutes, tells the person and their manager, and shows the stuck stretch. Reader: developers and team leads.

7.7

#### The Same Failure, Fought Separately by Three People

Who it's for Team leads and platform owners.

##### What it is

An article about several people struggling with the same failure without knowing others have it too.

##### Why it matters

A broken build (the step that turns code into a working product) may only come up weeks later, in a status meeting.

##### How it works for you

Kite Pulse groups failing commands and retries from across the whole team. It then points to the cause they share.

##### What you get

You see that it is one shared problem with one cause, rather than three people fighting it separately.

Optional By default, only admins can see Work Problems. The Blocker Board only works when AI labelling (an optional feature where an AI model labels sessions) is in use.

Original plan wording

The Same Failure, Fought Separately by Three People — A broken build surfaces weeks later in a status meeting; Kite Pulse groups failing commands and retries across the team and points at the shared cause. Reader: team leads and platform owners. Optional parts: Work Problems is admin by default; the Blocker Board needs AI labelling.

7.8

#### Solving the Same Bug Twice

Who it's for Engineering managers and the people who look after team knowledge.

##### What it is

An article about losing answers your team already found, so the same bug gets solved again.

##### Why it matters

The answer was in one person’s AI chat history, where nobody else could find it.

##### How it works for you

Kite Pulse keeps knowledge records that quote from real sessions.

##### What you get

Answers stay findable, so the next person does not have to solve the same bug from scratch.

Optional This only works when AI labelling (an optional feature where an AI model labels sessions) is in use.

Original plan wording

Solving the Same Bug Twice — The answer lived in one person's chat history; knowledge records quoted from real sessions keep it findable. Reader: engineering managers and knowledge owners. Optional parts: needs AI labelling.

7.9

#### When the Only Person Who Knows Moves On

Who it's for Managers and admins.

##### What it is

An article about parts of the work that depend on just one person, and what happens when they leave.

##### Why it matters

Parts of a product can quietly come to depend on a single person.

##### How it works for you

- Capability ownership shows the “bus factor”: how many people would need to leave before nobody knows a part of the product.
- The departure report lists what is at risk when someone leaves.

##### What you get

You see the risk while there is still time to act on it.

Optional This is for admins only by default.

Original plan wording

When the Only Person Who Knows Moves On — Parts of a product quietly depend on one person; capability ownership shows the bus factor and the departure report lists what is at risk while there is time. Reader: managers and admins. Optional parts: admin-only by default.

7.10

#### Project Status by Guesswork

Who it's for Engineering managers.

##### What it is

An article about knowing which projects are actually active, without guessing.

##### Why it matters

The question “which projects are active?” is usually answered from memory.

##### How it works for you

The All Projects page lists every project with:

- its health
- its contributors
- its last activity

Duplicate entries for the same project are merged into one.

##### What you get

One list of every project, with each project shown once, instead of an answer from memory.

Original plan wording

Project Status by Guesswork — Which projects are active is usually answered from memory; All Projects lists every project with health, contributors and last activity, and duplicates are merged. Reader: engineering managers.

7.11

#### AI-Written Changes Nobody Checked

Who it's for Tech leads and security teams.

##### What it is

An article about changes written by AI that nobody reviewed.

##### Why it matters

Unreviewed changes slip through, including ones that affect security.

##### How it works for you

Three things make these changes visible:

- the verification signal
- the Session Summary
- Security watch

##### What you get

Unchecked AI-written changes, including security-sensitive ones, become visible instead of slipping through.

Optional The verification signal and Security watch only work when AI labelling (an optional feature where an AI model labels sessions) is in use.

Original plan wording

AI-Written Changes Nobody Checked — Unreviewed changes, including security-sensitive ones, slip through; the verification signal, the Session Summary and Security watch make them visible. Reader: tech leads and security teams. Optional parts: the verification signal and Security watch need AI labelling.

7.12

#### Secrets Pasted into AI Chats

Who it's for Security teams.

##### What it is

An article about secrets and personal data that end up inside AI chats.

##### Why it matters

When people are stuck, they paste keys (secret codes that give access to software services) and personal data into their prompts to get unstuck.

##### How it works for you

- Kite Pulse hides (masks) known secrets, and does this twice.
- It lists leaked credentials and pasted secrets so someone can follow up on them.

##### What you get

Known secrets are masked, and you have a list of leaks to follow up.

Optional The list only fills when the server operator (the person who runs your Kite Pulse server) runs a scan. The pasted-secrets tab only works when AI labelling (an optional feature where an AI model labels sessions) is in use.

Original plan wording

Secrets Pasted into AI Chats — Keys and personal data get pasted into prompts to get unstuck; Kite Pulse masks known secrets twice and lists leaked credentials and pasted secrets for follow-up. Reader: security teams. Optional parts: the list fills when the server operator runs a scan; the pasted-secrets tab needs AI labelling.

7.13

#### Visibility Tools Developers Fight

Who it's for Leaders who have seen a monitoring rollout fail.

##### What it is

An article about why people push back against monitoring tools, and how Kite Pulse is different.

##### Why it matters

Tools that record keystrokes or screens make people resist them, and the data they produce ends up incomplete.

##### How it works for you

- Kite Pulse reads only the records the AI tools already keep themselves.
- It asks for consent.
- It shows each person what is collected about them.

##### What you get

Visibility built on the AI tools’ own records, with consent, and with each person able to see what is collected.

Original plan wording

Visibility Tools Developers Fight — Keystroke and screen loggers breed resistance and incomplete data; Kite Pulse reads only the AI tools' own records, asks for consent and shows each person what is collected. Reader: leaders who have seen a monitoring rollout fail.

7.14

#### Status Meetings and Timesheets as the Only Source of Truth

Who it's for Team leads and developers.

##### What it is

An article about relying on status meetings and timesheets as the only way to know what is happening.

##### Why it matters

When the only way to find out is to ask, people spend hours reporting on their work.

##### How it works for you

Kite Pulse builds the picture of the work from the AI sessions.

##### What you get

A picture of the work that comes from the sessions, not only from people reporting it.

Original plan wording

Status Meetings and Timesheets as the Only Source of Truth — When the only way to know is to ask, people spend hours reporting; Kite Pulse builds the picture from the sessions. Reader: team leads and developers.

7.15

#### The New Joiner Who Spends a Week Asking Around

Who it's for Managers who are onboarding new people.

##### What it is

An article about helping new joiners find out who owns what, using the Organizational Brain (Kite Pulse’s map of people, projects and documents).

##### Why it matters

Who owns what is “tribal knowledge”: it lives in people’s heads, so new joiners have to ask around.

##### How it works for you

The Organizational Brain puts people, projects and documents into one map. Anyone can explore it, within what they are allowed to access.

##### What you get

One map a new joiner can explore themselves, instead of spending a week asking around.

Optional The Brain must be switched on by an admin.

Original plan wording

The New Joiner Who Spends a Week Asking Around — Who owns what is tribal knowledge; the Organizational Brain puts people, projects and documents in one map anyone can explore within their access. Reader: managers onboarding people. Optional parts: Brain must be on (admin switch).

7.16

#### A Monthly AI Budget Discovered Too Late

Who it's for Engineering budget holders.

##### What it is

An article about spotting AI overspending before the month is over.

##### Why it matters

Teams only learn that they overspent when the month closes.

##### How it works for you

- Budgets send an alert when spending reaches 80% and again at 100%.
- The token pace line shows where usage is heading. (A token is a small piece of text the AI reads or writes; AI tools charge by tokens.)

##### What you get

Warning during the month, and a view of where usage is heading, instead of finding out after the month closes.

Optional Budgets are set by admins.

Original plan wording

A Monthly AI Budget Discovered Too Late — Teams learn they overspent when the month closes; budgets alert at 80% and 100%, and the token pace line shows where usage is heading. Reader: engineering budget holders. Optional parts: budgets are set by admins.

Category 8 of 13

## Organizational Brain and AI-Powered Intelligence

22 planned articles

This group of articles explains how Kite Pulse turns work sessions into understanding that the whole organisation can share. It covers three things: the Organizational Brain, which is optional (a shared map of your company and what it knows); the AI labelling layer, also optional, and what it makes possible; and the knowledge features. Many of those knowledge features use no AI at all.

Each entry below is a planned article. It says what the article covers, who it is written for, and which parts only work once someone switches them on.

8.1

#### The Organizational Brain: One Map of Your Company That Respects Who May See What

Who it's for Executives, admins and people evaluating Kite Pulse

##### What it is

The Organizational Brain (“the Brain”) is one shared map of your company inside Kite Pulse. This article explains what the Brain is.

##### Why it matters

A map of the whole company is only safe to use if it respects who may see what. The Brain is built around that rule.

##### How it works for you

- An admin switches the Brain on with one click.
- From then on, every map and every answer you see leaves out anything you are not allowed to read.

##### What you get

One map of your company that only ever shows each person what they may see.

Optional The Brain is off by default. An admin turns it on with a switch.

Original plan wording

The Organizational Brain: One Map of Your Company That Respects Who May See What — What the Brain is, how an admin switches it on with one click, and why every map and answer leaves out anything the viewer may not read. Reader: executives, admins and evaluators. Optional parts: off by default (admin switch).

8.2

#### Exploring the Brain Graph: How Departments, People, Projects and Tools Connect

Who it's for New joiners, team leads and leadership

##### What it is

The Brain Graph is an interactive map that shows how departments, people, projects and tools connect. It uses no AI.

##### Why it matters

It lets you see how the parts of the company link together: how departments, people, projects and tools connect to one another.

##### How it works for you

- You explore the map by interacting with it.
- You can open it in full-screen mode.
- It also has a place on the wall screen in The Office, Kite Pulse's 3D view of the workplace.

##### What you get

A picture of how departments, people, projects and tools connect, made without any AI.

Optional Works only when the Brain is on.

Original plan wording

Exploring the Brain Graph: How Departments, People, Projects and Tools Connect — The interactive map, its full-screen mode, and its place on The Office's wall screen. No AI. Reader: new joiners, team leads and leadership. Optional parts: Brain must be on.

8.3

#### Teaching the Brain: Documents and Project Context

Who it's for Department leads, managers and project owners

##### What it is

This article covers how you teach the Brain: by giving it your documents and the background of each project.

##### Why it matters

The Brain can use your company's own written guidance and each project's goals only once someone adds them.

##### How it works for you

- You upload policies, playbooks and SOPs (standard operating procedures: written step-by-step instructions). Each can be for the whole company, one department or one project.
- Any secrets in those documents, such as passwords or keys, are masked (hidden).
- You add objectives, strategy and status to project pages.

##### What you get

A Brain that holds your documents and project background, with secrets hidden.

Optional Works only when the Brain is on.

Original plan wording

Teaching the Brain: Documents and Project Context — Uploading policies, playbooks and SOPs for the company, a department or a project (secrets masked), and adding objectives, strategy and status to project pages. Reader: department leads, managers and project owners. Optional parts: Brain must be on.

8.4

#### Brain Agents: Focused Ways to Ask, from People & Org to an HR Policy Helper

Who it's for Department leads and admins

##### What it is

Brain agents are focused AI helpers you can put questions to. There are four built-in agents, plus department agents. The title names two examples, People & Org and an HR Policy Helper; the article covers the rest.

##### Why it matters

You get a focused way to ask a question without letting anyone see more than they already may.

##### How it works for you

- You choose one of the four built-in agents or a department agent, and ask it your question.
- The agent only reads and answers.
- It never widens access: it never lets anyone see more than they were already allowed to see.

##### What you get

Focused answers, without any change to who may see what.

Optional Works only when the Brain is on.

Original plan wording

Brain Agents: Focused Ways to Ask, from People & Org to an HR Policy Helper — The four built-in agents and department agents that only read and answer and never widen access. Reader: department leads and admins. Optional parts: Brain must be on.

8.5

#### Brain Chat: Ask the Organisation a Question and See Every Source

Who it's for Anyone looking for an answer inside the company

##### What it is

Brain Chat lets you ask the organisation a question. You get an answer and can see every source it came from.

##### Why it matters

When you can see where each part of an answer came from, you can check it. And it never shows you anything you are not allowed to read.

##### How it works for you

- You type a question.
- The answer cites its sources: knowledge records, project context, people's profiles, documents, and items from connected Jira (a project-tracking tool), HubSpot (a customer-records tool) or Slack (a team chat tool).
- Permissions are checked first, so only sources you may read are used.
- Brain Chat runs within a monthly spending budget, which is $20 by default.

##### What you get

Answers from inside the company, with every source shown and only material you are allowed to read, at a set monthly cost limit.

Optional The Brain must be on. You also need an AI key (an access key for an AI service), which the server operator provides. The server operator is whoever runs your Kite Pulse server.

Original plan wording

Brain Chat: Ask the Organisation a Question and See Every Source — Answers that cite knowledge records, project context, profiles, documents and connected Jira, HubSpot or Slack items, permission-checked first, within a monthly budget ($20 by default). Reader: anyone looking for an answer inside the company. Optional parts: Brain must be on, plus an AI key from the server operator.

8.6

#### Ask a Teammate's Agent, and See Who Asked Yours

Who it's for Developers

##### What it is

Each colleague has an agent you can ask about their recent work. Others can ask yours too, and you can see who did.

##### Why it matters

You can find out what a colleague has been doing on projects you share, while they stay in control. They see every question and can pause their agent.

##### How it works for you

- You ask about a colleague's last 14 days of synced work (work Kite Pulse has already collected), and only on projects you both work on.
- The text of their messages is never part of it.
- Your colleague sees every question that is asked.
- Your colleague can pause their agent.
- The same applies to you: you can see who asked your agent.

##### What you get

Answers about shared work, with full openness about who asked what.

Optional Works only when the Brain is on.

Original plan wording

Ask a Teammate's Agent, and See Who Asked Yours — Questions about a colleague's last 14 days of synced work on shared projects, never message text; the colleague sees every question and can pause their agent. Reader: developers. Optional parts: Brain must be on.

8.7

#### Your Brain Profile: What the Organisation Knows About You

Who it's for Every person

##### What it is

Your Brain profile is your own person page in the Brain. It shows what the organisation knows about you.

##### Why it matters

You can see for yourself what the organisation holds about you.

##### How it works for you

- Your person page has five tabs.
- One of them shows the exact AI Context text: the exact words about you that the AI is given.
- The article explains who can edit which parts.

##### What you get

A clear view of what is recorded about you, down to the exact text, and of who may change it.

Optional Works only when the Brain is on.

Original plan wording

Your Brain Profile: What the Organisation Knows About You — The five tabs of a person page, including the exact AI Context text, and who edits what. Reader: every person. Optional parts: Brain must be on.

8.8

#### Governing the Brain: What It Holds, Who Read It and How Long It Remembers

Who it's for Admins, department leads and compliance owners

##### What it is

The controls for overseeing the Brain: what it holds, who has read it, and how long it keeps things.

##### Why it matters

People responsible for oversight need to know what the Brain holds, who has read it and how long it remembers.

##### How it works for you

- For each department, you see what the Brain holds and who has read it.
- The budget (how much the Brain may spend on AI).
- The model (which AI model is used).
- Keep periods (how long things are kept).

##### What you get

A clear view, department by department, plus the settings for spending, the AI model and how long the Brain keeps things.

Optional Works only when the Brain is on.

Original plan wording

Governing the Brain: What It Holds, Who Read It and How Long It Remembers — Per-department holdings and readers, plus budget, model and keep periods. Reader: admins, department leads and compliance owners. Optional parts: Brain must be on.

8.9

#### AI Labelling, Done Carefully: Approved Label Lists, a Spending Cap and a Confidence Bar

Who it's for Admins and technical leads

##### What it is

AI labelling means an AI tags each piece of work with its type and its outcome.

##### Why it matters

Labels are only useful if they are done carefully: with labels an admin has approved, with spending kept in check, and with no guessing.

##### How it works for you

- Work is labelled by type and by outcome.
- An admin approves every list of labels.
- A spending cap limits what labelling can cost.
- A confidence bar sets how sure the AI must be. When it is not sure enough, the label is “unknown” rather than a guess.

##### What you get

Labels from lists you approved, at a capped cost, with “unknown” in place of guesses.

Optional Off until an admin sets it up with a provider key (the access key for the AI service that does the labelling).

Original plan wording

AI Labelling, Done Carefully: Approved Label Lists, a Spending Cap and a Confidence Bar — How work is labelled by type and outcome, with admin approval of every list and “unknown” instead of guesses. Reader: admins and technical leads. Optional parts: off until an admin sets it up with a provider key.

8.10

#### Checking the Labeller: Review Labels, the AI Call Log and Classification Reports

Who it's for Admins, and anyone asked to trust figures the AI produced

##### What it is

Three ways to check the AI that does the labelling (the “labeller”): Review Labels, the AI Call Log and Classification Reports.

##### Why it matters

If you are asked to trust figures made by an AI, you need a way to check them.

##### How it works for you

- Review Labels: you correct answers the AI was uncertain about.
- AI Call Log: you see every call made to the AI.
- Classification Reports (classification here means labelling): you see spend, coverage (how much work got labelled) and how well the model scores.

##### What you get

A way to correct, trace and measure the labeller's work.

Optional Needs AI labelling.

Original plan wording

Checking the Labeller: Review Labels, the AI Call Log and Classification Reports — Correcting uncertain answers, seeing every AI call, and spend, coverage and model scores. Reader: admins and anyone asked to trust AI-made figures. Optional parts: needs AI labelling.

8.11

#### From Facts to Advice: Fact Rules, Suggestion Rules and the Blocker Board

Who it's for Team leads and platform owners

##### What it is

Two kinds of rules that turn facts about work into advice: fact rules and suggestion rules. Suggestion rules feed the Blocker Board, a board of what is holding work up.

##### Why it matters

It moves you from bare facts to advice. The advice points to causes and actions, never at a person.

##### How it works for you

- Fact rules are free and use no AI.
- Suggestion rules have to be approved.
- Approved suggestion rules fill the Blocker Board with causes and actions, never a person.

##### What you get

Free facts without AI, and a board of causes and next actions that never points at a person.

Optional Suggestion rules and the Blocker Board need AI labelling. Fact rules do not.

Original plan wording

From Facts to Advice: Fact Rules, Suggestion Rules and the Blocker Board — Free no-AI fact rules, and approved suggestion rules that fill the Blocker Board with causes and actions, never a person. Reader: team leads and platform owners. Optional parts: suggestion rules and the Blocker Board need AI labelling.

8.12

#### What Labels Tell a Team: Trends, Team Review and AI Collaboration

Who it's for Engineering managers and team leads

##### What it is

What labels reveal about a whole team, shown as trends and in two views called Team Review and AI Collaboration.

##### Why it matters

You can see how the team's work changes over weeks and months, as figures for the team as a whole.

##### How it works for you

- You see pooled measures: figures combined across the team, not shown person by person.
- The measures are completion (whether work got finished), win rate (how often it succeeded), friction (where it got stuck) and checked changes (changes that were checked).
- They are shown over weeks and months.
- Figures for small teams are held back.

##### What you get

Team-level trends over time, with small teams held back.

Optional Needs AI labelling. Team Review and AI Collaboration are admin-only by default.

Original plan wording

What Labels Tell a Team: Trends, Team Review and AI Collaboration — Pooled measures of completion, win rate, friction and checked changes over weeks and months; small teams held back. Reader: engineering managers and team leads. Optional parts: needs AI labelling; Team Review and AI Collaboration are admin-only by default.

8.13

#### What Labels Tell One Person: My Day, the Verification Signal and Profile Facts

Who it's for Developers, and admins supporting them

##### What it is

What labels reveal about one person's own work: My Day, the Verification Signal and Profile Facts.

##### Why it matters

You get a view of your own day, your own habits with the AI, and your skills.

##### How it works for you

- My Day: a private daily summary of your work.
- Verification Signal: how often you check what the AI produced.
- Profile Facts: your skills and areas of work, shown on your developer page.

##### What you get

A private daily summary, a sense of how often you check AI output, and your skills and areas on your developer page.

Optional Needs AI labelling.

Original plan wording

What Labels Tell One Person: My Day, the Verification Signal and Profile Facts — A private daily summary, how often you check the AI's output, and skills and areas on the developer page. Reader: developers, and admins supporting them. Optional parts: needs AI labelling.

8.14

#### Knowledge Records: Lessons Quoted from Real Sessions, Linked to Where They Came From

Who it's for Engineering managers and knowledge owners

##### What it is

Knowledge records are lessons the organisation has learned, quoted from real work sessions.

##### Why it matters

A lesson is easier to trust when you can follow it back to where it came from.

##### How it works for you

- Each record captures something the organisation learned.
- It is quoted from a real session.
- It links to the sessions and commits it came from. A commit is a saved change in a project's code history.

##### What you get

A record of what the organisation learned, each lesson traceable to its source.

Optional Needs AI labelling. Admin-only by default.

Original plan wording

Knowledge Records: Lessons Quoted from Real Sessions, Linked to Where They Came From — What the organisation learned, with links to sessions and commits. Reader: engineering managers and knowledge owners. Optional parts: needs AI labelling; admin-only by default.

8.15

#### Keeping Knowledge Current: the Weekly Knowledge Log and Coherence Checks

Who it's for Knowledge owners and tech leads

##### What it is

Ways to keep knowledge records up to date: the Weekly Knowledge Log and coherence checks (checks that the records still fit together and are current).

##### Why it matters

Knowledge is only useful while it is current. Records that repeat each other, contradict each other or have gone out of date need to be found.

##### How it works for you

- The Weekly Knowledge Log shows the week's new records, grouped by kind.
- A “captured this week” card shows what was added this week.
- Coherence checks flag records that are duplicates, contradict each other, or are out of date.

##### What you get

A weekly view of new knowledge, and flags on records that need attention.

Optional Needs AI labelling.

Original plan wording

Keeping Knowledge Current: the Weekly Knowledge Log and Coherence Checks — The week's new records by kind, the “captured this week” card, and flags for duplicate, contradicting or out-of-date records. Reader: knowledge owners and tech leads. Optional parts: needs AI labelling.

8.16

#### The Capability Map: Describing Each Product in Plain Terms

Who it's for Product owners, architects and engineering managers

##### What it is

The Capability Map describes each of your products in plain terms. It uses no AI.

##### Why it matters

It gives everyone one plain description of what each product is made of and what it does.

##### How it works for you

- Each product is described by its modules (its main parts), its capabilities (what it can do) and its scenarios (situations in which it is used).
- Every change to the map is kept in a full change history.

##### What you get

A plain description of each product, with every change recorded, made without any AI.

Original plan wording

The Capability Map: Describing Each Product in Plain Terms — Modules, capabilities and scenarios with full change history. No AI. Reader: product owners, architects and engineering managers.

8.17

#### Who Really Knows This Part? Capability Ownership and the Bus Factor

Who it's for Engineering managers planning resilience

##### What it is

For each capability, this shows who really knows it. That covers who owns it and its bus factor: how few people hold the know-how, and so how exposed you are if they leave. It uses no AI.

##### Why it matters

To plan for resilience, you need to know which parts depend on too few people.

##### How it works for you

- You see who edits and who reads each capability.
- You see each person's share of the edits.
- You see the bus factor.
- You get hand-over hints.
- Owners can accept or decline.

##### What you get

A clear, AI-free picture of who knows each part, with hints for handing work over.

Original plan wording

Who Really Knows This Part? Capability Ownership and the Bus Factor — Who edits and reads each capability, shares of edits, bus factor and hand-over hints; owners accept or decline. No AI. Reader: engineering managers planning resilience.

8.18

#### When Someone Moves On: Tenure, the Departure Report and Knowledge-Capture Requests

Who it's for Managers and admins planning a hand-over

##### What it is

Tools for when someone leaves or changes role: tenure, the Departure Report and knowledge-capture requests. They show facts only.

##### Why it matters

When someone moves on, you need to plan the hand-over and know what is at risk.

##### How it works for you

- Tenure shows how long the person has been in the organisation, in their team and on each project.
- The Departure Report shows what is at risk.
- Knowledge-capture requests ask the person to write their knowledge down.

##### What you get

A fact-based hand-over plan: how long they have been there, what is at risk, and requests to write knowledge down.

Optional Admin-only by default. Works without the Brain.

Original plan wording

When Someone Moves On: Tenure, the Departure Report and Knowledge-Capture Requests — Time in organisation, team and project; what is at risk; requests to write knowledge down. Facts only. Reader: managers and admins planning a hand-over. Optional parts: admin-only by default; works without the Brain.

8.19

#### Project Notes: Every Version of CLAUDE.md, AGENTS.md, README and Decision Records

Who it's for Tech leads and architects

##### What it is

Project Notes keep every version of a project's own written knowledge. That means four kinds of file: CLAUDE.md and AGENTS.md (instruction files a project keeps for AI coding tools), the README (the project's introduction file) and decision records (written notes of decisions made).

##### Why it matters

A project's own written knowledge changes over time, so you need to see each version, what changed, and who has read it.

##### How it works for you

- You see the project's written knowledge version by version.
- You see what changed between versions.
- Secrets in the files are masked (hidden).
- Every read of these notes is recorded.

##### What you get

The full history of a project's written knowledge, with secrets hidden and a record of every read.

Optional Reading project notes is controlled by a switch that an admin turns on.

Original plan wording

Project Notes: Every Version of CLAUDE.md, AGENTS.md, README and Decision Records — A project's own written knowledge by version, with changes, secrets masked and every read recorded. Reader: tech leads and architects. Optional parts: project-notes read is an admin switch.

8.20

#### From Repeated Work to Reusable Skills: Session Graph and Skill Candidates

Who it's for DevEx (developer experience) and platform teams

##### What it is

The Session Graph groups similar work sessions together. Skill Candidates are drafts of reusable skills for Claude Code (an AI coding tool), made from workflows that repeat. A skill is a saved, reusable set of instructions. Neither uses AI.

##### Why it matters

Work that keeps repeating can be turned into something reusable.

##### How it works for you

- Similar sessions are grouped every day.
- From workflows that repeat, draft Claude Code skills are produced.

##### What you get

Daily groups of similar work and draft Claude Code skills from repeated workflows, made without any AI.

Original plan wording

From Repeated Work to Reusable Skills: Session Graph and Skill Candidates — Similar sessions grouped daily and draft Claude Code skills from repeated workflows. No AI. Reader: DevEx and platform teams.

8.21

#### Intelligence Without an AI Service: What Works With No Key at All

Who it's for Security, procurement and sceptical evaluators

##### What it is

This article lists everything in Kite Pulse that works with no AI service and no AI key at all.

##### Why it matters

If you are wary of AI services or are judging Kite Pulse, you need to know what works without one.

##### How it works for you

- Everything that runs with no AI is listed.
- Only two things need a key: AI labelling and Brain Chat.

##### What you get

A clear line between what works with no key and the two features that need one.

Original plan wording

Intelligence Without an AI Service: What Works With No Key at All — Everything that runs with no AI, and the two things that need a key (AI labelling and Brain Chat). Reader: security, procurement and sceptical evaluators.

8.22

#### Keeping Kite Pulse's Own AI Spend in Check

Who it's for Admins and finance owners

##### What it is

The controls that limit what Kite Pulse itself spends on AI.

##### Why it matters

Kite Pulse's own AI features cost money, so the people who own the budget need to keep that spend in check.

##### How it works for you

- The labelling cap: a spending limit for AI labelling.
- The Brain Chat budget.
- A separate key for agent questions: questions put to Kite Pulse through agents use their own AI key (an access key for an AI service), so that spend is kept apart.

##### What you get

Kite Pulse's own AI spend kept in check: a cap on labelling, a budget for Brain Chat, and agent questions kept on a separate key.

Optional Each control applies only when its own feature is on.

Original plan wording

Keeping Kite Pulse's Own AI Spend in Check — The labelling cap, the Brain Chat budget and the separate key for agent questions. Reader: admins and finance owners. Optional parts: each applies only when its feature is on.

Category 9 of 13

## 3D Visualization and Live Updates

14 planned articles

This tab covers The Office and how it stays up to date. The Office is Kite Pulse's live home page. It shows each person's AI agent sitting at a desk. The live updates keep The Office current, and they keep the team pages current too.

Each entry below is one planned article about The Office: what you see on screen, what the signs mean, who can see what, and how fresh the figures are. Read them in order for a full tour, or pick the part of the screen you want to understand.

9.1

#### The Office: a Live 3D Office Where Every Desk Is an AI Agent

Who it's for Everyone, and buyers who want to know what the home page is.

##### What it is

The Office is a live, three-dimensional picture of an office. It is the home page you land on, whatever your role.

##### Why it matters

You want to see the team's work at a glance, without opening reports or asking around.

##### How it works for you

The Office is laid out as rooms full of desks. Each desk holds a person's AI agent, not the person. So what you see at a desk is the AI agent's work.

##### What you get

One screen that shows the team's work at a glance, and it is the first thing every role sees.

Original plan wording

The Office: a Live 3D Office Where Every Desk Is an AI Agent — The default home page for every role: rooms of desks, each with a person's AI agent rather than the person, so the team's work shows at a glance. Reader: everyone, and buyers wanting to know what the home page is.

9.2

#### Reading an Agent's Body Language

Who it's for Every Office user.

##### What it is

The figure at each desk moves and poses to show what its AI agent is doing right now.

##### Why it matters

You need to read those movements to understand what The Office is telling you.

##### How it works for you

Watch the figure. The article explains each sign:

- Typing, reading or watching.
- Supervising sub-agents (helper agents that an AI agent starts to work alongside it).
- Waiting.
- Sitting in the lounge, when the person is away or has reached a plan limit (the usage cap on their Claude plan).
- Head down, when the agent is stuck.
- Walking in and out.
- A parcel, when code is pushed (sent up to the shared copy of the code).

##### What you get

You can tell what each agent is doing just by looking at the figure at its desk.

Original plan wording

Reading an Agent's Body Language — Typing, reading, watching, supervising sub-agents or waiting; the lounge when away or at a plan limit; head down when stuck; walking in and out; a parcel on a code push. Reader: every Office user.

9.3

#### One Marker per Desk: What “!”, a Thought Cloud and “Update” Are Telling You

Who it's for Team leads and developers.

##### What it is

Each desk shows one marker, such as a “!”, a thought cloud or the word “Update”. The marker flags something about that desk that you may need to know.

##### Why it matters

You need to know what each marker means so you can see which desks need your attention.

##### How it works for you

The article covers:

- Markers for: attention needed, stuck, at the plan limit, near the plan limit, waiting, syncing (sending its latest data), and out of date.
- Task lines that appear when you zoom in.
- Clicking a room to focus on it.

##### What you get

One quick sign per desk, with more detail as you zoom in or focus on a room.

Optional You see the details on why an agent is stuck and on plan use only for the people within your scope (the people your role lets you see in detail).

Original plan wording

One Marker per Desk: What “!”, a Thought Cloud and “Update” Are Telling You — Attention, stuck, plan limit, near limit, waiting, syncing and out-of-date markers, task lines on zoom, and clicking a room to focus. Reader: team leads and developers. Optional parts: stuck and plan detail only within your scope.

9.4

#### Live Without Pressing Refresh: How The Office and Team Overview Stay Current

Who it's for Team leads and technical evaluators.

##### What it is

The Office and the Team Overview page (a team-wide summary page) update by themselves. You never have to press refresh.

##### Why it matters

A live view is only useful if it is current, and you need to know how current it really is.

##### How it works for you

- Changes are sent to your screen within seconds.
- A “Live” badge shows that live updates are on.
- If the live connection drops, a 15-second fallback (a backup way of keeping the page updated) takes over, and the live connection reconnects by itself.
- Team Overview refreshes every 30 seconds.

##### What you get

A current view without effort, plus an honest limit: the figures are only as fresh as the latest upload from each person's computer.

Original plan wording

Live Without Pressing Refresh: How The Office and Team Overview Stay Current — Push updates within seconds, the “Live” badge, the 15-second fallback with automatic reconnection, Team Overview's 30-second refresh, and the honest limit: figures are as fresh as each computer's latest upload. Reader: team leads and technical evaluators.

9.5

#### The Office on the Wall: Full-Screen Mode for a TV or Meeting Room

Who it's for Team leads who run a team room.

##### What it is

A full-screen mode that shows The Office on a TV or a meeting-room screen.

##### Why it matters

Stand-ups (short daily team check-ins) and team rooms need a shared screen everyone can see.

##### How it works for you

Turn on full-screen mode. The wall screen shows no menus. You can choose a daylight theme or an evening theme.

##### What you get

A clean wall display of The Office for stand-ups and team rooms.

Optional The Brain view works only when the Brain (the Organizational Brain, Kite Pulse's optional shared map of the company, which has its own category of articles) is switched on.

Original plan wording

The Office on the Wall: Full-Screen Mode for a TV or Meeting Room — A menu-free wall screen with daylight or evening themes for stand-ups and team rooms. Reader: team leads running a team room. Optional parts: the Brain view needs the Brain on.

9.6

#### 3D, Map, List, Headroom and Brain: One Office, Five Ways to Look

Who it's for Everyone, including people on phones.

##### What it is

A view switch that shows The Office in five ways: 3D, Map, List, Headroom and Brain.

##### Why it matters

One view does not suit every person or every screen, for example a phone.

##### How it works for you

Use the view switch to pick a view:

- 3D: the three-dimensional office.
- Map.
- List: suited to phones.
- Headroom: a board of everyone's Claude plan usage, so you can see how close each person is to their limit.
- Brain: the Organizational Brain view.

##### What you get

The same office in the form that suits you, including on a phone.

Optional The Headroom view is for managers and admins. The Brain tab works only when the Brain is switched on.

Original plan wording

3D, Map, List, Headroom and Brain: One Office, Five Ways to Look — The view switch, including a List for phones and a Headroom board of everyone's Claude plan usage. Reader: everyone, including people on phones. Optional parts: Headroom is for managers and admins; the Brain tab needs the Brain on.

9.7

#### Click a Desk: Current Task, Stuck Reasons and Today's Figures in the Side Panel

Who it's for Team leads and managers.

##### What it is

When you click a desk, a side panel opens with details about that agent and its work.

##### Why it matters

A desk on its own shows only a sign. You sometimes need the facts behind it, such as the current task or why an agent is stuck.

##### How it works for you

Click a desk. What the panel shows depends on who you are:

- For everyone: the person's name, their presence (whether they are around) and the AI tool in use.
- Within your scope (the people your role lets you see in detail): the project, the task, the live step, the reasons it is stuck, the plan, the sync status, and today's figures.
- For admins only: the cost, on other people's desks.

##### What you get

The current task, stuck reasons and today's figures one click away, limited to what your role allows.

Original plan wording

Click a Desk: Current Task, Stuck Reasons and Today's Figures in the Side Panel — Name, presence and tool for everyone; project, task, live step, stuck reasons, plan, sync and today's figures within scope; cost on others' desks for admins only. Reader: team leads and managers.

9.8

#### Watching Sub-agents Work: Parallel Agents in The Office

Who it's for Developers and leads who run AI work in parallel.

##### What it is

The Office shows sub-agents (helper agents started by a main AI agent) working in parallel.

##### Why it matters

When AI work runs in parallel, you want to see each helper agent, not just the main one.

##### How it works for you

Sub-agents appear beside the agent that started them. Open the side panel to see each one's kind, the AI model it uses, how long it has run, and its current step.

##### What you get

A clear view of parallel AI work and what each sub-agent is doing.

Optional You see this detail only for the people within your scope.

Original plan wording

Watching Sub-agents Work: Parallel Agents in The Office — Sub-agents beside the agent that started them, with kind, model, run time and current step in the panel. Reader: developers and leads running parallel AI work. Optional parts: detail within scope only.

9.9

#### Catching a Stuck Agent in Half an Hour, Not at Next Week's Stand-up

Who it's for Team leads and developers.

##### What it is

How The Office shows a stuck agent, and how people are told about it.

##### Why it matters

A stuck agent should be caught within half an hour, not at next week's stand-up meeting.

##### How it works for you

- The article shows what a stuck agent looks like in The Office.
- An agent counts as “waiting” after two quiet minutes.
- After 30 minutes, a notice goes to the person and to their manager.

##### What you get

Stuck work is noticed in about half an hour, and both the person and their manager hear about it.

Optional The server operator (whoever runs your Kite Pulse server) can change the 30-minute interval or turn the notice off.

Original plan wording

Catching a Stuck Agent in Half an Hour, Not at Next Week's Stand-up — How a stuck agent looks in The Office, how “waiting” is worked out from two quiet minutes, and the 30-minute notice to the person and their manager. Reader: team leads and developers. Optional parts: the server operator can change the interval or turn it off.

9.10

#### The Activity Feed: the Last 24 Hours of the Office in One Stream

Who it's for Team leads and admins.

##### What it is

The Activity Feed is one running list of what happened in The Office over the last 24 hours.

##### Why it matters

You want to catch up on the past day in one place, instead of piecing it together.

##### How it works for you

The feed lists:

- Sessions (stretches of work with an AI tool).
- Tasks.
- Commits (saved sets of code changes).
- Agents getting stuck and getting unstuck.
- Approvals.
- Notes.
- Comings and goings.

The feed is worked out in your web browser and is never stored.

##### What you get

The last 24 hours of the office in one stream, with nothing extra kept on record.

Original plan wording

The Activity Feed: the Last 24 Hours of the Office in One Stream — Sessions, tasks, commits, stuck and unstuck agents, approvals, notes and comings and goings (worked out in the browser, never stored). Reader: team leads and admins.

9.11

#### The Tasks Board: Work in Progress, Stuck, Waiting, Paused, Failed and Done

Who it's for Team leads and admins.

##### What it is

The Tasks Board sorts work into six states: in progress, stuck, waiting, paused, failed and done.

##### Why it matters

You need to see where every piece of work stands, and what is waiting on you.

##### How it works for you

- Counters for each state; click one to filter the board.
- Approvals and uploads that are waiting for you.
- For admins: the processing queue (work waiting to be processed) and alerts.

##### What you get

One board that shows the state of all work and what needs your action.

Original plan wording

The Tasks Board: Work in Progress, Stuck, Waiting, Paused, Failed and Done — Filtering counters, approvals and uploads awaiting you, and the processing queue and alerts for admins. Reader: team leads and admins.

9.12

#### The Office Tab and the Connected Strip: the Team's Figures at a Glance

Who it's for Team leads and engineering managers.

##### What it is

The Office tab and the Connected Strip show the team's key figures in one place.

##### Why it matters

You want the team's numbers at a glance, without adding them up yourself.

##### How it works for you

The figures shown are:

- Agents, and how many are working, stuck or waiting.
- Sessions and commits today.
- Plan counts.
- Notes in the Brain.
- Connectors (links to other services) and skills (saved, reusable sets of instructions for AI tools) used.
- The AI tools and the code hosts (services where the code is kept) in use.

##### What you get

The team's figures at a glance.

Original plan wording

The Office Tab and the Connected Strip: the Team's Figures at a Glance — Agents, working, stuck, waiting, sessions and commits today, plan counts, notes in the Brain, connectors and skills used, and the AI tools and code hosts in use. Reader: team leads and engineering managers.

9.13

#### Finding People Fast: the Team Picker, Filter Tiles and One-Click Team Suggestions

Who it's for Team leads in larger organisations, and admins.

##### What it is

Tools for finding people quickly in The Office: a team picker, filter tiles and team suggestions.

##### Why it matters

In a larger organisation, the office has many desks and the people you want can be hard to find.

##### How it works for you

- Use the team picker to see one team's office.
- Use the filter tiles as quick filters.
- Admins get one-click team suggestions, based on who already works together.

##### What you get

You find the right people fast, and admins get team suggestions drawn from who already works together.

Original plan wording

Finding People Fast: the Team Picker, Filter Tiles and One-Click Team Suggestions — One team's office, quick filters, and admin team suggestions from who already works together. Reader: team leads in larger organisations and admins.

9.14

#### Presence, Not Surveillance: Who Sees What in The Office

Who it's for Developers, works councils (staff representative bodies) and privacy officers.

##### What it is

The rules for who can see what in The Office.

##### Why it matters

The Office should show presence, not act as surveillance. Staff and the people who protect their privacy need to know where the line is.

##### How it works for you

- Everyone sees presence (whether a person is around).
- Detail is shown only to people whose scope covers you.
- Message text is never shown.
- An admin can choose to hide other people's desks.
- Agent keys (passes that let people's own AI assistants ask Kite Pulse questions) have no access to The Office.

##### What you get

A clear, limited view of who sees what, which you can check against your privacy needs.

Original plan wording

Presence, Not Surveillance: Who Sees What in The Office — Presence for everyone, detail only within scope, never message text, an admin option to hide others' desks, and no access for agent keys. Reader: developers, works councils and privacy officers.

Category 10 of 13

## External API Access and Integrations

17 planned articles

This tab covers how Kite Pulse connects to the outside world, in both directions. Things come in: the ten AI coding tools it collects from. Things go out or are let in on purpose: the Agent API and MCP, two ways for your own AI assistants to ask Kite Pulse questions; Connectors, which link Kite Pulse to other work apps; user sync, which keeps people’s accounts up to date from your company’s staff directory; and delivery of messages to Slack and by email.

These articles are more technical than most. Each one explains one link between Kite Pulse and another tool or service: what it is, who controls it and what it lets through. A few terms come up often. An **API** is a way for one program to ask another program for information directly, without a person clicking through screens. **MCP** (Model Context Protocol) is a shared, standard way for AI assistants to plug into other tools and read from them. A **key** is a long secret code that works like a pass: whatever holds it can get in, but only as far as that key allows. A **connector** is a link between Kite Pulse and another work app. A **server operator** is the person who runs your Kite Pulse server. An **admin** is someone with admin rights in Kite Pulse.

10.1

#### Ten AI Coding Tools, One Integration Layer

Who it's for Technical evaluators and IT

##### What it is

Kite Pulse collects from ten AI coding tools out of the box, with nothing extra to build. This article explains which ten tools they are and how Kite Pulse reads each one.

##### Why it matters

Each AI coding tool already keeps its own session history, which is the record of the conversations people have with it. Kite Pulse reads that history rather than asking people to do anything new. Teams also need to control what is collected from each tool.

##### How it works for you

- Kite Pulse reads each tool’s own session history.
- Each tool has its own controls. You can switch a tool off completely.
- Or you can keep a tool on but collect counts only (just the numbers).

##### What you get

All ten tools come into one place through one shared way of bringing them in (the “integration layer”), and you decide tool by tool how much is collected.

Original plan wording

Ten AI Coding Tools, One Integration Layer — The ten tools collected out of the box, how their own session history is read, and per-tool controls (switch off, or counts only). Reader: technical evaluators and IT.

10.2

#### Kite Pulse for Claude Code Teams

Who it's for Teams that have standardised on Claude Code

##### What it is

Claude Code is Anthropic’s AI coding assistant. This article covers what Kite Pulse shows teams that use Claude Code as their main tool.

##### Why it matters

Claude plans have usage limits. A team that relies on Claude Code needs to know how close people are to those limits, which plan and version people are on, and how the tool’s agent features are being used.

##### How it works for you

- **Claude plan headroom:** how much room people have left before they reach their Claude plan limits.
- **Plan and version notices:** notices about people’s plans and about the Claude Code version they use.
- **The Agent features tab:** a tab about Claude Code’s agent features (an agent is an AI that carries out tasks on its own).
- **Inline sub-agent conversations:** a sub-agent is a helper the AI starts to do part of a job. You can read its conversation right inside the main session.
- **Skill Candidates:** in Claude Code, a skill is a saved, reusable set of instructions. Skill Candidates are draft skills made from work people repeat.
- **Agent Setup:** a view of how Claude Code is set up.

##### What you get

One view of Claude Code use across the team: plan limits, plans and versions, agent features, sub-agent work, skills and setup.

Optional Three parts are admin switches, meaning an admin decides whether they are on: the plan refresh (keeping the Claude plan figures up to date), the generation rate (how fast the AI produces its replies), and the reading of Claude Code’s setup that Agent Setup relies on.

Original plan wording

Kite Pulse for Claude Code Teams — Claude plan headroom, plan and version notices, the Agent features tab, inline sub-agent conversations, Skill Candidates and Agent Setup. Reader: teams standardised on Claude Code. Optional parts: plan refresh, generation rate and Agent Setup’s read are admin switches.

10.3

#### Kite Pulse for Cursor Teams

Who it's for Leads and finance on teams that use Cursor heavily

##### What it is

Cursor is a code editor with AI built in. This article covers what Kite Pulse shows teams that use Cursor a lot.

##### Why it matters

Leads need to see Cursor work next to work done in other tools. Finance needs to know which Cursor accounts exist and which plan each one is on.

##### How it works for you

- Cursor sessions appear in the shared timeline, alongside sessions from other tools.
- The Tool Accounts page lists Cursor accounts and each one’s plan tier, meaning its subscription level.
- You can connect Cursor to Kite Pulse over MCP, so the AI inside Cursor can ask Kite Pulse questions.

##### What you get

Cursor work in the same timeline as everything else, a clear list of Cursor accounts and plans, and the option to ask Kite Pulse questions from inside Cursor.

Optional The server operator has to turn MCP on.

Original plan wording

Kite Pulse for Cursor Teams — Cursor sessions in the shared timeline, Cursor accounts and plan tier in Tool Accounts, and connecting Cursor to Kite Pulse over MCP. Reader: leads and finance on Cursor-heavy teams. Optional parts: MCP is turned on by the server operator.

10.4

#### Kite Pulse for GitHub Copilot Users

Who it's for Organisations that use GitHub Copilot

##### What it is

GitHub Copilot is GitHub’s AI coding assistant. Copilot Chat is its chat, used inside VS Code, Microsoft’s code editor. This article covers what Kite Pulse shows for Copilot.

##### Why it matters

Organisations on Copilot need to see Copilot Chat work next to their other AI tools, and to know which Copilot accounts exist and which plans they are on.

##### How it works for you

- Copilot Chat in VS Code appears alongside the other tools.
- Kite Pulse lists Copilot accounts.
- It can optionally read which Copilot plan each person has.
- You can connect VS Code to Kite Pulse over MCP, so the AI in VS Code can ask Kite Pulse questions.

##### What you get

Copilot use in the same view as your other tools, a list of Copilot accounts, plan names if an admin turns that on, and the option to ask Kite Pulse questions from VS Code.

Optional Reading the Copilot plan is an admin switch, meaning an admin decides whether it is on. The server operator has to turn MCP on.

Original plan wording

Kite Pulse for GitHub Copilot Users — Copilot Chat in VS Code alongside other tools, Copilot accounts, the optional Copilot plan read, and connecting VS Code over MCP. Reader: organisations on GitHub Copilot. Optional parts: plan read is an admin switch; MCP is turned on by the server operator.

10.5

#### Kite Pulse for Codex and Gemini CLI

Who it's for Teams that use AI agents in the terminal

##### What it is

Codex and Gemini CLI are AI coding agents that run in the terminal, the text window where developers type commands. This article covers what Kite Pulse shows for them.

##### Why it matters

Teams using these terminal tools want that work captured too, without asking people to take extra steps.

##### How it works for you

- Sessions with these terminal agents are captured without any extra steps.
- Kite Pulse lists Codex accounts.
- Gemini usage is priced, but the cost shown is an estimate.
- The models (the AI models behind the tools) appear on the Models tab.

##### What you get

Terminal agent work in the same view as everything else, with Codex accounts, an estimated cost for Gemini and the models used.

Original plan wording

Kite Pulse for Codex and Gemini CLI — Terminal agent sessions captured without extra steps, Codex accounts, Gemini usage priced as an estimate, and models on the Models tab. Reader: teams using terminal-based AI agents.

10.6

#### Kite Pulse for Aider, Cline, Roo Code, Kilo Code and OpenCode

Who it's for Teams that use any of these five tools

##### What it is

Aider, Cline, Roo Code, Kilo Code and OpenCode are five more AI coding tools. This article explains how they join the same view as the other tools.

##### Why it matters

Teams using these tools want them in the same picture as everything else, and want to know where the cost figures come from.

##### How it works for you

Work in these five tools appears in the same view as your other tools. Their cost figures come from what the tools themselves report, and the article explains why.

##### What you get

These five tools in the same view as the rest, and a clear account of where their cost figures come from.

Original plan wording

Kite Pulse for Aider, Cline, Roo Code, Kilo Code and OpenCode — How these tools join the same view and why their cost comes from the tools’ own reports. Reader: teams using any of these five tools.

10.7

#### Agent API Keys: Letting Your Own AI Assistant Ask Kite Pulse

Who it's for Admins and security reviewers

##### What it is

The Agent API is Kite Pulse’s way for AI assistants to ask it questions directly. To use it, an assistant needs a key, which works like a pass. This article covers those keys.

##### Why it matters

Letting an AI assistant read your data needs firm limits. A key must never show more than its owner is allowed to see.

##### How it works for you

- An admin issues the keys to individual people.
- Each key has its own permissions, an expiry date and limits.
- A key never sees more than its owner can see.
- A person can cancel (revoke) their own key from the Account page.

##### What you get

Your own AI assistant can ask Kite Pulse questions, within limits an admin sets and never beyond what the key’s owner can see.

Optional The server operator has to turn this on.

Original plan wording

Agent API Keys: Letting Your Own AI Assistant Ask Kite Pulse — Admin-issued keys per person with permissions, expiry and limits, never seeing more than their owner; self-revocation under Account. Reader: admins and security reviewers. Optional parts: turned on by the server operator.

10.8

#### Chat Mode or Direct Access: Choosing How Much an AI Tool Can Read

Who it's for Admins and security reviewers

##### What it is

There are two levels of access for an AI tool that holds a key: Chat mode and Direct access. This article explains the choice.

##### Why it matters

Admins need to decide how much an outside AI tool can read, and keep the cost of answering its questions separate.

##### How it works for you

- **Chat mode:** the AI tool can only ask questions. Kite Pulse’s own assistant answers them.
- **Direct access:** the AI tool can read data, but only within what the key’s owner can see.
- A separate key for the AI provider (the company whose model does the answering) keeps these costs apart.

##### What you get

You choose how much an AI tool can read, and its costs stay apart from your other costs.

Optional Once keys are turned on, the admin chooses which mode to use.

Original plan wording

Chat Mode or Direct Access: Choosing How Much an AI Tool Can Read — Questions only, answered by Kite Pulse’s own assistant, or read access within the owner’s view; a separate provider key keeps costs apart. Reader: admins and security reviewers. Optional parts: admin choice once keys are on.

10.9

#### Connecting Claude Code, Cursor and VS Code to Kite Pulse over MCP

Who it's for People who work inside an AI assistant

##### What it is

MCP is a standard way for AI assistants to plug into other tools. This article explains how to connect Claude Code, Cursor and VS Code to Kite Pulse this way.

##### Why it matters

People who spend their day inside an AI assistant want to ask Kite Pulse questions from there, without switching screens.

##### How it works for you

- The setup is ready-made, so you do not have to work it out yourself.
- Once connected, your assistant gets about 115 read tools (ready-made ways to look data up), all limited to what the key’s owner is allowed to see.
- Some things are deliberately not offered over MCP, and the article explains what they are.

##### What you get

Kite Pulse answers inside the AI assistant you already use, within your own permissions.

Optional The server operator has to turn MCP on, and an admin has to issue the key.

Original plan wording

Connecting Claude Code, Cursor and VS Code to Kite Pulse over MCP — Ready-made setup, about 115 read tools within the owner’s permissions, and what is deliberately not offered over MCP. Reader: people who work inside an AI assistant. Optional parts: server operator turns it on; an admin issues the key.

10.10

#### Questions Your AI Assistant Can Answer About Engineering

Who it's for Managers who work through an AI assistant

##### What it is

This article shows the kinds of engineering questions your AI assistant can answer once it is connected to Kite Pulse.

##### Why it matters

Managers who work through an AI assistant want to ask about their team’s engineering work from inside that assistant.

##### How it works for you

You ask your assistant, and it answers from Kite Pulse. The question areas are:

- team review;
- the blocker board (what is holding work up);
- plan history;
- the costliest turns (single exchanges with the AI);
- how use splits across models;
- effort per branch (a branch is a separate line of work in the code);
- how quickly newcomers get up to speed;
- file hotspots, the files that get the most attention;
- failure rates;
- cost reconciliation, checking cost figures against each other;
- time lost to interruptions.

##### What you get

Answers to everyday engineering questions, asked from the AI assistant you already work in.

Optional Direct access (the mode in which the AI tool can read data itself) is an admin choice. Some answers also need AI labelling or optional reads (extra things Kite Pulse reads only when they are switched on).

Original plan wording

Questions Your AI Assistant Can Answer About Engineering — Team review, blocker board, plan history, costliest turns, model splits, effort per branch, newcomer ramp-up, file hotspots, failure rates, cost reconciliation and time lost to interruptions. Reader: managers who work through an AI assistant. Optional parts: Direct access is an admin choice; some answers need AI labelling or optional reads.

10.11

#### Reading What the AI Said: the Session-Text Permission and Its Safeguards

Who it's for Security reviewers and data-protection officers

##### What it is

Session text is the actual wording of the conversation with the AI. Reading it needs its own permission. This article covers that permission and the safeguards around it.

##### Why it matters

The words of a conversation are more sensitive than counts and totals, so reading them needs extra protection.

##### How it works for you

- It is a separate permission from the others.
- Granting it requires acknowledging the risk.
- Secrets in the text are masked.
- Every read is recorded.
- It is never available over MCP.

##### What you get

A clear, controlled way to read what the AI said, with every read on record.

Original plan wording

Reading What the AI Said: the Session-Text Permission and Its Safeguards — A separate permission with a risk acknowledgement, masked secrets, every read recorded, never over MCP. Reader: security reviewers and data-protection officers.

10.12

#### Before and After Handing Out a Key: Try a Question and Agent Activity

Who it's for Admins and auditors

##### What it is

Two tools that help with keys: Try a Question, used before you hand a key out, and Agent Activity, used after.

##### Why it matters

Before giving out a key, an admin wants to know exactly what an AI tool would see. Afterwards, admins and auditors want to see how the key is being used.

##### How it works for you

- **Before:** with Try a Question, you preview exactly what an AI tool would get back.
- **After:** Agent Activity shows the keys and their usage, and every request is in the log.

##### What you get

No surprises before a key goes out, and a full record of every request after.

Original plan wording

Before and After Handing Out a Key: Try a Question and Agent Activity — Preview exactly what an AI tool would get back, then see keys, usage and every request in the log. Reader: admins and auditors.

10.13

#### Connectors: Linking Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion to Projects

Who it's for Admins and project owners

##### What it is

A connector is a link between a Kite Pulse project and another work app. This article covers connectors to seven apps:

- Jira (task tracking)
- HubSpot (customer records)
- Slack (team chat)
- GitHub (where code is stored)
- Confluence (team wiki)
- Google Drive (shared files)
- Notion (notes and documents)

##### Why it matters

A project’s work also lives in these other apps. Linking them to the project brings that context closer.

##### How it works for you

- Admins link the apps to projects, and the article explains how.
- Brain Chat is where you ask questions of Kite Pulse’s Brain. It can cite connected Jira, HubSpot and Slack items in its answers.
- It only cites items the person asking is allowed to see.

##### What you get

Projects linked to the apps your team already uses, and Brain Chat answers that point to the Jira, HubSpot and Slack items behind them.

Optional Citations only work when the Brain is turned on and there is an AI key (an access key for an AI service).

Original plan wording

Connectors: Linking Jira, HubSpot, Slack, GitHub, Confluence, Google Drive and Notion to Projects — How admins link them, and how Brain Chat can cite connected Jira, HubSpot and Slack items within the asker’s permissions. Reader: admins and project owners. Optional parts: citations need the Brain on and an AI key.

10.14

#### User Sync with Microsoft Entra ID and Okta

Who it's for IT and identity administrators

##### What it is

Microsoft Entra ID and Okta are services companies use to manage staff accounts. User sync keeps Kite Pulse accounts in step with them.

##### Why it matters

When people join, change or leave, their Kite Pulse accounts should follow without someone updating them by hand.

##### How it works for you

- Accounts are created, updated and deactivated automatically.
- It never sets roles.
- It never touches admin accounts.
- This is provisioning, meaning accounts are set up and kept up to date automatically. It is not single sign-on, which would mean logging in to Kite Pulse with your company login.

##### What you get

Kite Pulse accounts that follow your staff directory, while roles and admin accounts stay under your own control.

Optional This is an admin switch, meaning an admin decides whether it is on.

Original plan wording

User Sync with Microsoft Entra ID and Okta — Accounts created, updated and deactivated automatically; never sets roles or touches admins; provisioning, not single sign-on. Reader: IT and identity administrators. Optional parts: admin switch.

10.15

#### Server Alerts in Your Slack Channel

Who it's for Admins and IT on-call staff

##### What it is

Kite Pulse can post alerts about its own infrastructure (the server and the systems it runs on) to a channel in Slack, a team chat app.

##### Why it matters

The people on call need to hear about server problems in a place they are already watching.

##### How it works for you

- Infrastructure alerts go to your Slack channel.
- A Test button lets you send a test.
- A delivery history shows what was sent.

##### What you get

Server alerts in your team’s Slack channel, a way to test that it works, and a record of deliveries.

Optional This is an admin switch, meaning an admin decides whether it is on.

Original plan wording

Server Alerts in Your Slack Channel — Infrastructure alerts to Slack, the Test button and delivery history. Reader: admins and IT on-call. Optional parts: admin switch.

10.16

#### Email from Kite Pulse: Notices, Alert Emails, Daily Digests and Scheduled Reports

Who it's for Admins and leadership

##### What it is

This article explains, from start to finish, how Kite Pulse sends email. There are four kinds:

- notices;
- alert emails;
- daily digests (a once-a-day summary);
- scheduled reports.

##### Why it matters

Different people need to hear about different things, so someone has to decide who is told what.

##### How it works for you

Admins decide who is told what. Kite Pulse then sends the notices, alert emails, daily digests and scheduled reports by email.

##### What you get

The right messages reach the right people by email, as decided by your admins.

Optional The server operator has to set up mail first.

Original plan wording

Email from Kite Pulse: Notices, Alert Emails, Daily Digests and Scheduled Reports — The email channel end to end, with admins deciding who is told what. Reader: admins and leadership. Optional parts: needs the server operator to set up mail.

10.17

#### What Leaves Your Server, Integration by Integration

Who it's for Security and IT decision-makers

##### What it is

A list of every link from your Kite Pulse server to the outside, and the switch that controls each one.

##### Why it matters

Security and IT need to know exactly what can leave the server, and which switch controls each link.

##### How it works for you

The article goes through each outward link in turn, with the switch that controls it:

- AI providers (the companies whose AI models are used);
- agent keys (the keys that let AI assistants ask Kite Pulse questions);
- Slack;
- email;
- user sync.

##### What you get

One clear list of what leaves your server and the switch for each link.

Original plan wording

What Leaves Your Server, Integration by Integration — Every outward link and the switch that controls it: AI providers, agent keys, Slack, email and user sync. Reader: security and IT decision-makers.

Category 11 of 13

## Workflows, Productivity, and Decision-Making

16 planned articles

Each article in this tab walks you through one process you repeat with Kite Pulse, step by step, and names the decisions that process helps you make.

Read each article as a routine: the Kite Pulse pages you go through, in order, and the decision you come away with at the end.

11.1

#### Running the Monday Stand-up from The Office and Team Overview

Who it's for Team leads.

##### What it is

How to run your Monday stand-up (a short team check-in) using two Kite Pulse pages: The Office, Kite Pulse's 3D view of the team, and Team Overview.

##### Why it matters

At the start of the week you need to know where everyone is and what they are working on before you can decide who needs support.

##### How it works for you

- See who is online and coding.
- See who needs attention.
- See who works on what.
- Then decide who to pair up, who to help and who to unblock.

##### What you get

A clear answer to who to pair, help or unblock this week.

Original plan wording

Running the Monday Stand-up from The Office and Team Overview — Who is online and coding, who needs attention, who works on what; then who to pair, help or unblock. Reader: team leads.

11.2

#### Sprint Planning Around Plan Headroom, Leave and On-Call

Who it's for Engineering managers and team leads.

##### What it is

How to plan a sprint (a short, fixed block of work) around three things: plan headroom (how much room people have left before they hit their Claude plan limits), who is on leave, and who is on call (the person who handles urgent issues).

##### Why it matters

Heavy AI work should go to people who have the plan room and the time for it, so you check before you assign.

##### How it works for you

- Check plan pressure: how close people are to their plan limits.
- Check who is on leave.
- Check recent activity.
- Then assign the heavy AI work.

##### What you get

A decision on who takes the large tasks, and when.

Optional The plan figures cover Claude Code (Anthropic's AI coding tool) only, not other tools. Background refresh is an admin switch: an admin decides whether it is on.

Original plan wording

Sprint Planning Around Plan Headroom, Leave and On-Call — Checking plan pressure, leave and recent activity before assigning heavy AI work. Decision: who takes the large tasks, and when. Reader: engineering managers and team leads. Optional parts: Claude Code only; background refresh is an admin switch.

11.3

#### The Monthly AI Spend and Budget Review

Who it's for Finance, budget holders and managers.

##### What it is

A monthly routine for reviewing what your organisation spends on AI tools and how that compares with budget.

##### Why it matters

Budgets and paid seats (licences for a tool) need regular checking so you can adjust them while it still makes a difference.

##### How it works for you

- Look at usage broken down by team, by project, by tool and by model (the specific AI model used).
- Look at the 30-day outlook.
- Look at budget alerts.
- Look at Tool Accounts and seat prices.

##### What you get

Two decisions: whether to adjust budgets, and whether to buy, move or cancel seats.

Original plan wording

The Monthly AI Spend and Budget Review — Usage by team, project, tool and model, the 30-day outlook, budget alerts, Tool Accounts and seat prices. Decisions: adjust budgets; buy, move or cancel seats. Reader: finance, budget holders and managers.

11.4

#### From “AI Agent Stuck” Notice to Fix

Who it's for Developers and team leads.

##### What it is

What to do, step by step, when Kite Pulse shows an “AI Agent Stuck” notice. An AI agent is an AI tool that carries out a task on its own.

##### Why it matters

A stuck agent is lost time, and you need to know whether the problem is one person's task or something the whole team keeps running into.

##### How it works for you

- Open the agent's desk (in The Office, Kite Pulse's live 3D view, each person's AI agent sits at a desk).
- Read “What the agent did”.
- Restart the agent with a clearer request.
- Check Work Problems.

##### What you get

A decision: is this one person's task to fix, or does it need a team-wide fix?

Original plan wording

From “AI Agent Stuck” Notice to Fix — Open the desk, read “What the agent did”, restart with a clearer request, check Work Problems. Decision: one person's task or a team-wide fix? Reader: developers and team leads.

11.5

#### The Weekly Team Health Review, Without Ranking Anyone

Who it's for Engineering managers.

##### What it is

A weekly review of how the team is doing, done without ranking any person against another.

##### Why it matters

The aim is to find causes of lost time that the team shares, not to judge individuals.

##### How it works for you

- Go through Team Review.
- Go through Trends.
- Go through the Blocker Board.

##### What you get

A decision on which shared cause of lost time to fix next.

Optional This needs AI labelling to be turned on, and only admins can see it by default.

Original plan wording

The Weekly Team Health Review, Without Ranking Anyone — Team Review, Trends and the Blocker Board. Decision: which shared cause of lost time to fix next. Reader: engineering managers. Optional parts: needs AI labelling; admin-only by default.

11.6

#### A Release Retrospective Built on Session Evidence

Who it's for Team leads and managers.

##### What it is

How to run a release retrospective (a look back after a release at what went well and what did not) using evidence from sessions, meaning the recorded conversations people had with their AI coding tools.

##### Why it matters

Basing the look-back on what actually happened in sessions tells you what to change before the next release.

##### How it works for you

- Look at Workflows & Pain Points.
- Look at the sessions that hurt.
- Look at the new decisions in the knowledge log.

##### What you get

A decision on what to change before the next release.

Optional The knowledge log needs AI labelling to be turned on.

Original plan wording

A Release Retrospective Built on Session Evidence — Workflows & Pain Points, the sessions that hurt, and the knowledge log's new decisions. Decision: what to change before the next release. Reader: team leads and managers. Optional parts: the knowledge log needs AI labelling.

11.7

#### Onboarding a New Hire, from Account to First Synced Session

Who it's for Managers and admins.

##### What it is

The full path for bringing a new team member onto Kite Pulse, from creating their account to the moment their first session reaches the server.

##### Why it matters

A newcomer is only set up once their sessions are actually flowing in, and you also have to decide which of their projects should sync.

##### How it works for you

- The account.
- The desktop program and the KP- code (a code that starts with “KP-”).
- The Onboarding Wizard.
- Approval.
- Watch Workspace until sessions flow.

##### What you get

A newcomer whose sessions are syncing, and a decision on which projects they sync.

Original plan wording

Onboarding a New Hire, from Account to First Synced Session — Account, desktop program and KP- code, Onboarding Wizard, approval, and watching Workspace until sessions flow. Decision: which projects the newcomer syncs. Reader: managers and admins.

11.8

#### Planning a Hand-over Before Someone Moves On

Who it's for Managers and admins.

##### What it is

How to plan a hand-over when someone is about to leave or change roles.

##### Why it matters

When a person moves on, their work needs new owners, and some of what they know must be written down before they go.

##### How it works for you

- Check the bus factor (how few people know a piece of work, so that losing one of them would leave it stranded).
- Read the departure report.
- Use capture requests (requests to get what the person knows written down).
- Confirm the new owners.

##### What you get

A decision on who takes over what, and what must be written down first.

Optional Only admins can see this by default.

Original plan wording

Planning a Hand-over Before Someone Moves On — Bus factor, the departure report, capture requests and confirming new owners. Decision: who takes over what, and what must be written down first. Reader: managers and admins. Optional parts: admin-only by default.

11.9

#### The Monthly Project Portfolio Review

Who it's for Managers and admins.

##### What it is

A monthly look across all your projects together.

##### Why it matters

Each month you need to decide where people go and which projects should carry on, stop, combine or end.

##### How it works for you

- Look at each project's health, phase and blockers.
- Look at shared projects.
- Look at merges and paused projects.

##### What you get

A decision on what to staff, pause, merge or retire.

Optional Phase and blockers need AI labelling to be turned on.

Original plan wording

The Monthly Project Portfolio Review — Health, phase and blockers, shared projects, merges and paused projects. Decision: what to staff, pause, merge or retire. Reader: managers and admins. Optional parts: phase and blockers need AI labelling.

11.10

#### Leadership Reporting on Autopilot

Who it's for Managers and executives.

##### What it is

Setting up reports for leadership that arrive on a schedule, so nobody has to put them together by hand each time.

##### Why it matters

Leaders need a steady picture to decide where to put their attention and their AI budget.

##### How it works for you

- A regular rhythm of scheduled company reports.
- A periodic plan usage report.

##### What you get

A decision on where to invest attention and AI budget.

Optional Admins set up the schedules.

Original plan wording

Leadership Reporting on Autopilot — A rhythm of scheduled company reports and a periodic plan usage report. Decision: where to invest attention and AI budget. Reader: managers and executives. Optional parts: admins set up schedules.

11.11

#### The Admin's Daily Health Check

Who it's for Admins and IT.

##### What it is

A daily check an admin runs to see that Kite Pulse itself is working properly.

##### Why it matters

Problems are best fixed before users notice them.

##### How it works for you

- Look at the infrastructure tiles (the summary boxes about the systems Kite Pulse runs on).
- Work through the alert workflow.
- Look at Machines, Data Collection and Processing.

##### What you get

A decision on what to fix before users notice.

Original plan wording

The Admin's Daily Health Check — Infrastructure tiles, the alert workflow, Machines, Data Collection and Processing. Decision: what to fix before users notice. Reader: admins and IT.

11.12

#### Choosing Which AI Tools and Models to Standardise On

Who it's for Engineering leadership and DevEx leads (the people responsible for developers' tools and ways of working).

##### What it is

How to choose which AI tools and AI models your organisation settles on as standard.

##### Why it matters

You need to decide which tools are worth paying for, where paid seats can be combined, and which models to point people towards.

##### How it works for you

- Look at Models.
- Look at Agent features.
- Look at Tool Accounts and seat prices.

##### What you get

Three decisions: which tools to fund, which seats to consolidate, and which models to recommend.

Original plan wording

Choosing Which AI Tools and Models to Standardise On — Models, Agent features, Tool Accounts and seat prices. Decisions: which tools to fund, seats to consolidate, models to recommend. Reader: engineering leadership and DevEx leads.

11.13

#### Turning Repeated Work into Team Standards

Who it's for Platform and DevEx teams.

##### What it is

How to spot work people keep repeating and turn it into a shared team standard.

##### Why it matters

Repeated work is the natural thing to automate or standardise next.

##### How it works for you

- Look at Workflows & Pain Points.
- Look at Skill Candidates.
- Look at Agent Setup.
- Look at the Claude Code version check.

##### What you get

A decision on what to automate or standardise next.

Optional Agent Setup needs its optional read to be switched on (an extra piece of information the desktop program collects only when that read is switched on).

Original plan wording

Turning Repeated Work into Team Standards — Workflows & Pain Points, Skill Candidates, Agent Setup and the Claude Code version check. Decision: what to automate or standardise next. Reader: platform and DevEx teams. Optional parts: Agent Setup needs its optional read.

11.14

#### A Developer's Own Weekly Review

Who it's for Developers.

##### What it is

A weekly review you run on your own work.

##### Why it matters

Looking back at your own week helps you pick one habit to change.

##### How it works for you

- Look at Workspace.
- Look at the Top 3.
- Find your costly sessions in My Sessions.
- Look at My Day.

##### What you get

A decision on one habit to change next week.

Optional My Day needs AI labelling to be turned on.

Original plan wording

A Developer's Own Weekly Review — Workspace, the Top 3, costly sessions in My Sessions, and My Day. Decision: one habit to change next week. Reader: developers. Optional parts: My Day needs AI labelling.

11.15

#### Weekly Security Triage of AI Conversations

Who it's for Security and IT.

##### What it is

A weekly triage (sorting by urgency) of security issues found in people's conversations with AI tools.

##### Why it matters

You need to know which exposures to act on first. Masking a key in Kite Pulse does not revoke (cancel) that key at its provider, so a leaked key still needs action at the source.

##### How it works for you

- Look at Leaked Credentials, sorted by status.
- Look at sensitive changes nobody has checked yet.
- Look at pasted secrets.
- Follow up.

##### What you get

A decision on which exposures to act on first, with the reminder that masking does not revoke a key at its provider.

Optional The scan is run by the server operator (the person who runs your Kite Pulse server). The tabs need AI labelling to be turned on.

Original plan wording

Weekly Security Triage of AI Conversations — Leaked Credentials by status, unchecked sensitive changes and pasted secrets, and follow-up. Decision: which exposures to act on first; masking does not revoke a key at its provider. Reader: security and IT. Optional parts: scan run by the server operator; tabs need AI labelling.

11.16

#### Keeping the Project List True Week to Week

Who it's for Admins and approvers.

##### What it is

A weekly routine for keeping Kite Pulse's list of projects accurate.

##### Why it matters

You need to know which projects are really separate and which ones should sync.

##### How it works for you

- Clear approvals.
- Act on merges and splits.
- Review Request History.

##### What you get

A decision on which projects are really separate and which should sync.

Original plan wording

Keeping the Project List True Week to Week — Clearing approvals, acting on merges and splits, and reviewing Request History. Decision: which projects are really separate and which should sync. Reader: admins and approvers.

Category 12 of 13

## Industry-Specific Applications

11 planned articles

These articles show how an organisation in a particular sector, or of a particular shape, could use the features Kite Pulse has today. None of them claims a certification, a compliance status or a feature the product does not have.

Each article picks one kind of organisation, from a small agency to a large enterprise or a solo developer, and shows which existing Kite Pulse features fit it. Read them as “how this type of team would apply the product”, not as new features.

12.1

#### How Software Agencies and Consultancies Could Use Kite Pulse

Who it's for Agency owners and delivery leads.

##### What it is

A look at how a company that does software work for clients could use Kite Pulse to see the effort behind each client project.

##### Why it matters

An agency runs several client engagements at once and needs a clear picture of each one. The article is about that clarity per engagement — it is not about billing clients.

##### How it works for you

- See the effort that went into each client project.
- Export a developer’s work for a chosen period.
- See when personal AI tool accounts were used for client work.
- Link a client’s Jira (a work-tracking tool) or HubSpot (a customer-relationship tool) to the matching project.

##### What you get

A clear view of each client engagement. It is meant for understanding the work, not for producing invoices.

Original plan wording

How Software Agencies and Consultancies Could Use Kite Pulse — Effort per client project, developer exports for a period, personal accounts used for client work, and client Jira or HubSpot linked to projects. Clarity per engagement, not billing. Reader: agency owners and delivery leads.

12.2

#### Self-Hosted AI Development Insight for Finance and Healthcare Teams

Who it's for IT, security and risk leads in regulated organisations.

##### What it is

A look at how finance and healthcare teams could see how their developers use AI while keeping everything on systems they run themselves (“self-hosted”).

##### Why it matters

Regulated organisations need to know where their data goes and who can see it. The article is careful here: it makes no compliance claims at all.

##### How it works for you

- Kite Pulse runs on your own infrastructure — no vendor cloud.
- Secrets (such as passwords and keys) are masked twice.
- People’s consent comes first.
- There is an audit log (a record of who did what) that cannot be edited.
- No AI service is needed.

##### What you get

Insight into AI-assisted development on infrastructure you control. Be aware of the limit the article states: erasing a person’s data makes it anonymous rather than removing everything.

Original plan wording

Self-Hosted AI Development Insight for Finance and Healthcare Teams — Your own infrastructure, no vendor cloud, secrets masked twice, consent first, an audit log that cannot be edited, and no AI service needed. Explicitly no compliance claims; erasure anonymises rather than removes everything. Reader: IT, security and risk leads in regulated organisations.

12.3

#### Running Kite Pulse Across an Enterprise with Many Teams

Who it's for Enterprise engineering leadership and IT.

##### What it is

A look at how a large organisation with many teams could run Kite Pulse, in its own AWS account (Amazon’s cloud service, under the organisation’s own control).

##### Why it matters

With many teams, you need to control who sees what, share out the work of managing accounts, and keep people and teams up to date.

##### How it works for you

- Permissions decide who can see and do what.
- Managing accounts can be handed to other people (delegated).
- Users can be synced from Entra ID or Okta (company directory services, where a company keeps its list of staff accounts). This is user sync only — it is not single sign-on (logging in with your company account).
- Teams are recorded with dates.
- Each team can have a budget.
- The Organisation Overview page shows the whole organisation, and reports can be scheduled.

##### What you get

One Kite Pulse set-up that works across many teams, running in your own AWS account.

Original plan wording

Running Kite Pulse Across an Enterprise with Many Teams — Permissions, delegated account management, user sync from Entra ID or Okta (not single sign-on), dated teams, team budgets, Organisation Overview and scheduled reports, in your own AWS account. Reader: enterprise engineering leadership and IT.

12.4

#### Kite Pulse for Startups: Small Team, Big AI Bill

Who it's for Founders and first engineering leads.

##### What it is

A look at how a small startup with a large AI bill could use Kite Pulse.

##### Why it matters

A small team can spend a lot on AI tools, and in a small team some parts of the product may depend on just one person.

##### How it works for you

- Start on one machine.
- Watch how much room is left on your Claude plan (Claude is Anthropic’s AI assistant, sold on plans with usage limits) and how fast tokens are being used. Tokens are small pieces of text the AI reads or writes; tools charge by tokens.
- Set a monthly budget.
- Spot the parts of the product that only one person works on.

##### What you get

A view of AI spending and single-person areas that fits a small team. Note the limit the article states: some measures that are pooled across the whole team are held back when the team is very small.

Original plan wording

Kite Pulse for Startups: Small Team, Big AI Bill — Starting on one machine, watching Claude plan headroom and token pace, a monthly budget, and spotting one-person parts of the product. Some pooled team measures hold back very small teams. Reader: founders and first engineering leads.

12.5

#### Distributed and Outsourced Teams Across Time Zones

Who it's for Heads of distributed engineering and vendor managers.

##### What it is

A look at how teams spread across time zones, including outsourced teams, could use Kite Pulse.

##### Why it matters

When people work at different hours and in different places, it is hard to know who is around, who is away and how work is going.

##### How it works for you

- In The Office (Kite Pulse’s 3D view, covered in its own category), see who is present and follow the Activity feed.
- Use Leave & On-Call to see who is away and who is on call.
- See work patterns.
- Offline catch-up: when a computer has been offline, the desktop program catches up once the connection is back.
- Each lead sees only their own reporting line.

##### What you get

A shared picture of a team across time zones, with each lead limited to the people who report to them.

Original plan wording

Distributed and Outsourced Teams Across Time Zones — Presence and the Activity feed in The Office, Leave & On-Call, work patterns and offline catch-up, with each lead limited to their own reporting line. Reader: heads of distributed engineering and vendor managers.

12.6

#### Public Sector and Government IT Teams

Who it's for Public-sector IT and digital teams.

##### What it is

A look at how government and public-sector IT teams could use Kite Pulse. It makes no accreditation claims.

##### Why it matters

Public-sector teams need control over where data lives, which AI features run and how long data is kept.

##### How it works for you

- It runs on infrastructure you control.
- AI features are off, or used only if you opt in.
- An audit log records who did what.
- Brain Governance, the controls for the Brain (Kite Pulse’s Organizational Brain feature, covered in its own category of this plan).
- Retention windows set how long data is kept.

##### What you get

Insight into AI-assisted work on infrastructure you control, with AI features under your choice — and no claim of accreditation.

Original plan wording

Public Sector and Government IT Teams — Infrastructure you control, AI features off or opt-in, the audit log, Brain Governance and retention windows. No accreditation claims. Reader: public-sector IT and digital teams.

12.7

#### Coding Bootcamps and Engineering Education

Who it's for Bootcamp and course leads.

##### What it is

A look at how coding bootcamps and engineering courses could use Kite Pulse — always with the learners’ consent.

##### Why it matters

Teachers want to see how a group of learners works with AI and review that work with them, while learners keep a say over their own data.

##### How it works for you

- See how a cohort (a group of learners) works with AI.
- Use Session Playback (replaying a recorded AI session) for guided review.
- Look at the verification signal.
- Each learner has their own Privacy page.

##### What you get

A consent-based way to see and review how learners use AI, with each learner having their own Privacy page.

Optional The verification signal only works when AI labelling (Kite Pulse using an AI model to label sessions) is in use.

Original plan wording

Coding Bootcamps and Engineering Education — With learners’ consent: how a cohort works with AI, Session Playback for guided review, the verification signal, and each learner’s own Privacy page. Reader: bootcamp and course leads. Optional parts: the verification signal needs AI labelling.

12.8

#### Game and Product Studios

Who it's for Studio technical directors and producers.

##### What it is

A look at how game and product studios, which run several titles or products at once, could use Kite Pulse.

##### Why it matters

A studio works on several titles at once and needs to see, for each one, its Capability Map, its project health and which AI tools and models it depends on.

##### How it works for you

- See the Capability Map for each product.
- Compare project health across titles.
- Show The Office (Kite Pulse’s 3D view, covered in its own category) on a wall screen in the studio.
- See which AI tools and models each project relies on.

##### What you get

One view across all of the studio’s titles, including which AI tools and models each one relies on.

Original plan wording

Game and Product Studios — The Capability Map per product, project health across titles, The Office on a studio wall screen, and which AI tools and models each project relies on. Reader: studio technical directors and producers.

12.9

#### Platform and Developer-Experience Teams

Who it's for Platform and DevEx (developer-experience) leads.

##### What it is

A look at how platform and developer-experience teams — the people who build shared tools and standards for other developers — could use Kite Pulse.

##### Why it matters

These teams need to find the friction many developers share and roll out standards across the organisation.

##### How it works for you

The article uses these parts of Kite Pulse to find shared friction and roll out standards:

- Work Problems
- Workflows & Pain Points
- Agent features
- Agent Setup
- Skill Candidates
- The version check
- Machines

##### What you get

A way to see where developers get stuck in common and to roll out shared standards.

Original plan wording

Platform and Developer-Experience Teams — Work Problems, Workflows & Pain Points, Agent features, Agent Setup, Skill Candidates, the version check and Machines to find shared friction and roll out standards. Reader: platform and DevEx leads.

12.10

#### Independent Developers and Freelancers

Who it's for Solo developers.

##### What it is

A look at how a developer working alone could run all of Kite Pulse on one computer.

##### Why it matters

A solo developer works across several AI tools and projects and may want a record of that work without it leaving their machine.

##### How it works for you

- Everything runs on one computer.
- You keep a private record of your AI-assisted work across tools and projects.
- You see your own Claude plan usage and your own scorecard.
- Nothing leaves the machine.

##### What you get

A private record of your own AI-assisted work, kept entirely on your computer.

Original plan wording

Independent Developers and Freelancers — Everything on one computer: a private record of AI-assisted work across tools and projects, own plan usage and scorecard, nothing leaving the machine. Reader: solo developers.

12.11

#### IT and Security Teams Watching AI Adoption

Who it's for CISOs (chief information security officers) and IT managers.

##### What it is

A look at how IT and security teams could use Kite Pulse to keep watch on how AI tools are being taken up across the organisation.

##### Why it matters

As AI tools spread, security teams need to know when personal accounts are used, and when credentials have leaked.

##### How it works for you

- Personal accounts are revealed by their email domain (the part of the address after the @).
- Leaked Credentials lists credentials (such as passwords and keys) that have turned up in AI conversations.
- Security watch looks out for other security risks.
- Tool switches turn collection off for individual AI tools, and counts-only collection gathers token counts only.

##### What you get

A security-focused view of AI adoption: personal accounts, leaked credentials and security concerns in one place.

Optional The Leaked Credentials list fills after the server operator runs a scan. Security watch only works when AI labelling (Kite Pulse using an AI model to label sessions) is in use.

Original plan wording

IT and Security Teams Watching AI Adoption — Personal accounts revealed by email domain, Leaked Credentials, Security watch, and tool switches with counts-only collection. Reader: CISOs and IT managers. Optional parts: the list fills after an operator scan; Security watch needs AI labelling.

Category 13 of 13

## Getting Started and Practical Guides

19 planned articles

These are step-by-step how-to guides, and each one ends with something that works. Several of them come in pairs with a feature article in category 2, 8, 9 or 10: the feature article explains what a part of Kite Pulse is, and the guide shows you how to set it up.

Each card is one planned guide. It says who the guide is for, what it walks you through, and which steps only work once someone has switched something on.

13.1

#### Install Kite Pulse on Your Own Computer in One Command

Who it's for Individual developers.

##### What it is

A guide to putting all of Kite Pulse on your own computer with one command. That means the server (the part that receives your session history), the console (the pages where you look at it) and the desktop program (the part that picks up your AI tools' history) all run on one machine.

##### Why it matters

If you are one developer working alone, you can run every part yourself on the one computer you already use.

##### How it works for you

- Run the one install command.
- Sign in.
- Set your password.
- Confirm your projects.
- Watch your sessions appear.

##### What you get

A working Kite Pulse on your own computer, showing your own sessions.

Original plan wording

Install Kite Pulse on Your Own Computer in One Command — Server, console and desktop program on one machine; sign in, set your password, confirm projects and watch sessions appear. Reader: individual developers.

13.2

#### Run a Team Pilot on One Machine on Your Local Network

Who it's for Team leads and admins who are trying Kite Pulse out.

##### What it is

A guide to running a trial (a pilot) of Kite Pulse for a team, on one machine that sits on your office or home network.

##### Why it matters

Before a full rollout, you can try Kite Pulse with a few colleagues using a single machine they can reach.

##### How it works for you

- Set up a pilot server that your colleagues can reach over the local network.
- Create their accounts.
- Bring the first people on board with their KP- codes (the joining codes that start with “KP-”).

##### What you get

A working team pilot, with the first colleagues joined.

Original plan wording

Run a Team Pilot on One Machine on Your Local Network — A pilot server colleagues can reach, accounts, and onboarding the first people with their KP- codes. Reader: team leads and admins trialling Kite Pulse.

13.3

#### Set Up a Team Server on Ubuntu or in Your Own AWS Account

Who it's for IT staff and the people who run servers.

##### What it is

A guide to setting up a proper team server, either on Ubuntu (a widely used Linux system for servers) or in your own AWS account (Amazon's cloud service).

##### Why it matters

A team needs a server it runs itself, and this guide covers the two ready-made ways to set one up, plus a server-only choice.

##### How it works for you

- The Ubuntu script sets up the server with HTTPS (the secure web connection) that renews itself.
- The AWS script shows you its plan and asks you before it goes ahead.
- The server-only option sets up just the server.

##### What you get

A working team server on Ubuntu or in your own AWS account.

Original plan wording

Set Up a Team Server on Ubuntu or in Your Own AWS Account — The Ubuntu script with self-renewing HTTPS, the AWS script that shows its plan and asks first, and the server-only option. Reader: IT and server operators.

13.4

#### Rolling Kite Pulse Out to Your Team

Who it's for Admins who are leading a rollout.

##### What it is

A guide to the settings an admin works through when bringing Kite Pulse to the whole team.

##### Why it matters

A rollout needs decisions about how people sign up, who can do what, and who must be approved before their data comes in.

##### How it works for you

- Choose the sign-up mode.
- Set roles and managers.
- Work through the Setup checklist.
- Enter the Organisation Name.
- Decide on onboarding approval.

##### What you get

A team rollout with sign-up, roles, managers and approvals in place.

Optional User sync is a switch an admin turns on. It does not replace signing in with email and password.

Original plan wording

Rolling Kite Pulse Out to Your Team — Sign-up mode, roles and managers, the Setup checklist, Organisation Name, and onboarding approval. Reader: admins leading a rollout. Optional parts: user sync is an admin switch and does not replace email-and-password sign-in.

13.5

#### Joining Your Team's Kite Pulse: KP- Code, Onboarding Wizard and First Sync

Who it's for New team members.

##### What it is

A guide for someone joining a team that already uses Kite Pulse: using their KP- code (the joining code that starts with “KP-”), going through the Onboarding Wizard (the step-by-step setup screens) and getting to the first sync (the first time their data is sent).

##### Why it matters

New people need to know the steps, and that an empty console before approval is expected, not a fault.

##### How it works for you

- Install the program.
- Enter your code.
- Confirm your projects.
- Wait for approval.
- Understand why your console is empty until then: that is expected.

##### What you get

You are joined to your team's Kite Pulse and your first sync goes through.

Original plan wording

Joining Your Team's Kite Pulse: KP- Code, Onboarding Wizard and First Sync — Install, enter your code, confirm projects, wait for approval, and why an empty console before then is expected. Reader: new team members.

13.6

#### “My Pages Are Empty”: Checking That Your Work Is Being Captured

Who it's for Developers, and the admins helping them.

##### What it is

A guide to checking, step by step, that your work is actually being picked up when your pages look empty.

##### Why it matters

Empty pages leave you unsure whether your work is being captured, so you need a way to check.

##### How it works for you

- Check your Wizard status and your approval status.
- Check your projects' states on the Workspace page.
- Look at upload retries (uploads that are being tried again).
- Use the tray menu (the desktop program's small icon): View log, Re-enter code and Run diagnostics.

##### What you get

You can tell whether your work is being captured.

Original plan wording

“My Pages Are Empty”: Checking That Your Work Is Being Captured — Wizard and approval status, project states on Workspace, upload retries, and the tray's View log, Re-enter code and Run diagnostics. Reader: developers and the admins helping them.

13.7

#### How to Read Your Scorecard

Who it's for Developers.

##### What it is

A guide to reading your own Scorecard, part by part.

##### Why it matters

The Scorecard has many parts, and some of what is on it only you can see, so it helps to know what each part means.

##### How it works for you

- The Top 3.
- Verdicts, with their reasons, evidence and suggestions.
- What “not enough data” means.
- The tiles.
- Patterns.
- Your working style.
- What only you see.

##### What you get

You can read your Scorecard and understand each part of it.

Optional The verification signal only appears when AI labelling is in use (see guide 13.14).

Original plan wording

How to Read Your Scorecard — The Top 3, verdicts, reasons, evidence and suggestions, “not enough data”, tiles, patterns, working style, and what only you see. Reader: developers. Optional parts: the verification signal needs AI labelling.

13.8

#### Set Up Monthly AI Budgets, Seat Prices and Hourly Rates

Who it's for Admins and finance.

##### What it is

A guide to entering the money figures: monthly AI budgets, seat prices (what you pay per person for each tool) and hourly rates.

##### Why it matters

You want to be warned as spending nears and reaches a budget, and to have each tool's price and each role level's hourly cost recorded.

##### How it works for you

- Set monthly budgets, with alerts at 80% and at 100%.
- Enter a seat price for each tool.
- Enter an hourly cost for each role level.

##### What you get

Budgets with alerts, seat prices per tool and hourly costs per role level, all set up.

Original plan wording

Set Up Monthly AI Budgets, Seat Prices and Hourly Rates — Budgets with 80% and 100% alerts, seat prices per tool, hourly cost per role level. Reader: admins and finance.

13.9

#### Configure Roles, Permissions and Delegated Account Management

Who it's for Admins.

##### What it is

A guide to deciding who can see which pages and who can manage accounts.

##### Why it matters

Managers need access to certain pages, and account management can be handed to others instead of resting with admins alone.

##### How it works for you

- Give managers access to particular pages.
- Hand account management to someone else (delegate it).
- If you choose to, hide other people's desks in The Office (Kite Pulse's 3D view, where each person's AI agent sits at a desk).

##### What you get

Roles, page access and account management set the way you want.

Original plan wording

Configure Roles, Permissions and Delegated Account Management — Granting pages to managers, delegating account management, and optionally hiding other people's desks in The Office. Reader: admins.

13.10

#### How to Set Up Collection, Step by Step: Tools, Counts-Only and Optional Reads

Who it's for Admins and IT.

##### What it is

A step-by-step guide to choosing what Kite Pulse collects: which AI tools, whether to collect counts only, and which extra (optional) reads to switch on.

##### Why it matters

You decide what is collected, tool by tool and read by read, rather than taking everything.

##### How it works for you

- Turn each tool on or off.
- Use counts-only collection.
- Switch on each optional read, one by one, under Retention.

##### What you get

Collection set up the way you chose.

Optional Every extra read stays off until an admin turns it on.

Original plan wording

How to Set Up Collection, Step by Step: Tools, Counts-Only and Optional Reads — Turning each tool on or off, counts-only collection, and switching on each optional read on Retention. Reader: admins and IT. Optional parts: every extra read is off until an admin turns it on.

13.11

#### Set Up Project Approvals and Detection Rules

Who it's for Admins and approvers.

##### What it is

A guide to the rules for how new projects are spotted and approved, and how projects are removed.

##### Why it matters

You decide whether new projects and new people need someone's OK, and how long a deletion waits before it takes effect.

##### How it works for you

- Decide whether new projects need to be confirmed.
- Turn onboarding approval on or off.
- Make changes later.
- Set the deletion grace period (a waiting time before a deletion takes effect).

##### What you get

Project approval and detection working by your rules.

Original plan wording

Set Up Project Approvals and Detection Rules — Whether new projects need confirmation, onboarding approval on or off, later changes, and the deletion grace period. Reader: admins and approvers.

13.12

#### Configure Notifications and Alerts

Who it's for Admins.

##### What it is

A guide to setting up who gets told about what, and how the messages reach them.

##### Why it matters

The right people need to hear about the right things, by email or Slack (a team chat app), and you want to see what was actually delivered.

##### How it works for you

- Choose who is told what.
- Set up email and the daily digest (a once-a-day summary).
- Connect a Slack channel and check it with its Test button.
- Set the thresholds (the levels at which an alert fires).
- Look at the delivery history.
- Personal notices reach people automatically, with nothing to set up.

##### What you get

Notifications and alerts going to the right people, with a record of what was sent.

Optional Email only works once the server operator has set up mail. Slack is a switch an admin turns on.

Original plan wording

Configure Notifications and Alerts — Who is told what, email and the daily digest, a Slack channel with its Test button, thresholds and delivery history; personal notices arrive automatically. Reader: admins. Optional parts: email needs the server operator to set up mail; Slack is an admin switch.

13.13

#### Get Fresher Claude Plan Figures with the Background Refresh

Who it's for Admins.

##### What it is

A guide to the background refresh, which keeps the Claude plan figures (how close people are to their Claude plan limits) more up to date.

##### Why it matters

Plan figures are more useful when they are fresh.

##### How it works for you

- Switch the background refresh on.
- Choose how often it runs.
- Developers can opt out.
- Set how long readings are kept.

##### What you get

Fresher Claude plan figures.

Optional It is a switch an admin turns on, and it works for Claude Code (Anthropic's AI coding tool) only.

Original plan wording

Get Fresher Claude Plan Figures with the Background Refresh — Switching it on, choosing how often it runs, developer opt-out, and how long readings are kept. Reader: admins. Optional parts: admin switch; Claude Code only.

13.14

#### Set Up AI Labelling Safely

Who it's for Admins.

##### What it is

A guide to setting up AI labelling (an optional feature where an AI model labels sessions) safely, with a key, a spending cap, approved label lists and logs to check.

##### Why it matters

AI labelling uses an outside AI provider, so you want spending capped, each label list approved and a record of the calls made.

##### How it works for you

- On the Classification page, enter the provider key and a monthly cap.
- Approve each label list.
- Use Review Labels.
- Check the AI Call Log.
- Set suggestion rules for the Blocker Board.

##### What you get

AI labelling running within the limits and lists you approved.

Optional AI labelling is off until an admin sets it up. Fact rules need no AI.

Original plan wording

Set Up AI Labelling Safely — Provider key and monthly cap on Classification, approving each label list, Review Labels, the AI Call Log, and suggestion rules for the Blocker Board. Reader: admins. Optional parts: off until an admin sets it up; fact rules need no AI.

13.15

#### Switch On the Organizational Brain and Add Your First Documents

Who it's for Admins and department leads.

##### What it is

A guide to switching on the Organizational Brain (the part of Kite Pulse where you add your organisation's own documents) and putting in your first ones.

##### Why it matters

The Brain only helps once it is on and has your documents and project context in it.

##### How it works for you

- Turn it on with one click.
- Add your first SOPs (standard operating procedures) and policies.
- Add project context.
- Set up a department agent.
- Set the Chat budget.

##### What you get

A working Brain with your first documents in it.

Optional Only an admin can switch the Brain on. Chat needs an AI key from the server operator.

Original plan wording

Switch On the Organizational Brain and Add Your First Documents — One-click switch, first SOPs and policies, project context, a department agent and the Chat budget. Reader: admins and department leads. Optional parts: Brain switch is admin-only; Chat needs an AI key from the server operator.

13.16

#### Connect Your AI Assistant to Kite Pulse over MCP

Who it's for Admins and developers.

##### What it is

A guide to connecting your AI assistant to Kite Pulse over MCP (a standard way for AI assistants to connect to other tools and data).

##### Why it matters

It lets the AI assistant you already use reach Kite Pulse.

##### How it works for you

- Choose Chat mode or Direct access.
- Issue a key.
- Test the key with “Try a question”.
- Connect Claude Code, Cursor or VS Code (AI coding tools and code editors).

##### What you get

Your AI assistant connected to Kite Pulse.

Optional Keys only work once the server operator turns them on.

Original plan wording

Connect Your AI Assistant to Kite Pulse over MCP — Chat mode or Direct access, issuing a key, testing it with “Try a question”, and connecting Claude Code, Cursor or VS Code. Reader: admins and developers. Optional parts: server operator turns keys on.

13.17

#### Set Retention Windows and Handle Data Requests

Who it's for Admins and data-protection leads.

##### What it is

A guide to setting how long each kind of data is kept (retention windows) and handling requests to export or erase data.

##### Why it matters

You need to decide how long data is kept and be able to answer export and erase requests.

##### How it works for you

- Set retention for each kind of data.
- Look at the deletion schedule, which is a preview only.
- Handle export requests and erase requests.

##### What you get

Retention set for each kind of data, and a way to handle data requests.

Optional Real deletion only happens once the server operator turns it on.

Original plan wording

Set Retention Windows and Handle Data Requests — Retention per kind of data, the preview-only deletion schedule, and export or erase requests. Reader: admins and data-protection leads. Optional parts: real deletion is turned on by the server operator.

13.18

#### Schedule Reports for Leadership

Who it's for Admins and engineering managers.

##### What it is

A guide to scheduling reports that go to leadership by email.

##### Why it matters

Leadership needs reports on a regular schedule, in their inbox.

##### How it works for you

- Choose a company report or a developer report.
- Have it sent by email daily, weekly or monthly.
- Preview it.
- See the send history.
- Set who has permission to download it.

##### What you get

Reports reaching leadership on schedule.

Original plan wording

Schedule Reports for Leadership — Company or developer reports by email daily, weekly or monthly, preview, send history and download permission. Reader: admins and engineering managers.

13.19

#### Keep the Desktop Program Up to Date Across Machines

Who it's for Admins and IT.

##### What it is

A guide to keeping the Kite Pulse desktop program up to date on every machine.

##### Why it matters

The desktop program runs on many machines, and each one needs to stay on the current version.

##### How it works for you

- Publish a new version.
- Watch the Machines page for each machine's update status and app logs.
- Act on the “Update” marker in The Office.

##### What you get

The desktop program kept up to date across your machines.

Original plan wording

Keep the Desktop Program Up to Date Across Machines — Publishing a version, watching Machines for update status and app logs, and acting on The Office's “Update” marker. Reader: admins and IT.

Reference

## Coverage map

Which articles cover each area and audience

**Every product area and every audience has at least one article, seen from more than one angle.** This tab is the plan's own check that nothing is left uncovered.

Numbers are "category.article", so 2.9 means category 2, article 9. A range such as 2.1–2.3 means articles 2.1, 2.2 and 2.3. Click any number to jump to that article. A dash (—) means the plan has no article of that kind for that area.

### By product area

For each part of the product, the plan names three kinds of article: one that says what the feature is, one that talks about the benefit it brings or the problem it solves, and one that shows it in a story, a routine workflow or a step-by-step guide.

| Product area | What it is (feature articles) | Benefit or problem articles | Story, workflow or guide articles |
| --- | --- | --- | --- |
| Capture across ten tools | 2.1–2.3, 10.1–10.6 | 4.8, 7.5 | 13.10 |
| Your own pages and sessions | 2.4–2.10 | 4.1–4.3, 4.6–4.9 | 3.3, 3.9, 3.14, 11.14, 13.6–13.7 |
| The Office, 3D view and live updates | 9.1–9.14 | 4.10, 5.1 | 3.1, 11.1 |
| Team and organisation views | 2.11–2.15 | 5.4, 5.6, 5.9, 6.1–6.2 | 3.12, 11.5 |
| Projects | 2.16–2.17 | 5.7, 7.10 | 3.5, 11.9, 11.16, 13.11 |
| AI usage, cost and budgets | 2.18–2.25 | 5.10, 5.13, 6.3–6.5, 7.3, 7.16 | 3.6, 11.3, 11.12, 13.8 |
| Claude plan limits | 2.26–2.27 | 4.4, 5.3, 7.4 | 3.2, 11.2, 13.13 |
| Work problems and stuck agents | 2.14, 9.9 | 4.5, 5.2, 5.5, 7.6–7.7 | 3.4, 11.4 |
| Reports | 2.28 | 5.12 | 3.11, 11.10, 13.18 |
| Notifications and alerts | 2.10, 2.30, 10.15–10.16 | 4.13, 6.13 | 11.11, 13.12 |
| AI labelling | 8.9–8.13, 8.22 | 6.14, 7.11 | 13.14 |
| Knowledge and stewardship | 8.14–8.20 | 5.11, 6.8–6.9, 7.8–7.9 | 3.7, 3.13, 11.6, 11.8, 11.13 |
| Organizational Brain | 8.1–8.8, 8.21 | 4.12, 7.15 | 3.8, 13.15 |
| Agent API, MCP and assistants | 10.7–10.12 | — | 3.15, 13.16 |
| Connectors and user sync | 10.13–10.14 | — | 12.1, 12.3 |
| Administration and security | 2.29–2.32, 10.17 | 6.10–6.12, 7.12 | 3.10, 11.15, 13.4, 13.9, 13.17, 13.19 |
| Privacy and trust | 1.7, 1.13, 9.14 | 4.11, 6.6–6.7, 7.13 | 12.2 |
| Deployment | 1.14 | 4.14, 6.11 | 13.1–13.3, 12.10 |

### By audience

Where each kind of reader should start.

| Audience | Main articles |
| --- | --- |
| Individual developers | Category 4, 3.3, 3.9, 3.14, 11.14, 12.10, 13.1, 13.5–13.7 |
| Team leads and engineering managers | Category 5, 3.1–3.2, 3.12, 11.1–11.9 |
| Executives and finance | 1.5, 6.1–6.5, 3.6, 3.11, 11.3, 11.10, 11.12 |
| Admins, IT and security | 6.10–6.13, 11.11, 11.15–11.16, 12.11, categories 2 (administration) and 13 |
| HR, people teams and works councils | 1.7, 6.6–6.7, 6.9, 9.14 |
| Platform and DevEx teams (the teams that look after developers' tools and working environment) | 5.13, 3.13, 11.13, 12.9 |
| Sector-specific readers | Category 12 |

### Not covered yet, on purpose

Three things have no article yet. All three need the next release of the desktop program, and articles will be added when it ships:

- The exact "approval" and "waiting" signals from Claude Code.
- Plan figures taken from the status line.
- Lists of plugins in Agent Setup.

Source: the Claude Doc "Kite Pulse — Article Plan" (28 October 2026). This page rewrites it in plain language; the plan's exact words for each article are kept under "Original plan wording".
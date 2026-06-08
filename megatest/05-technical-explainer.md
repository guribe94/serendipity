# What Happens When You Load a Web Page

You type a URL into your browser, hit Enter, and a fraction of a second later a web page appears. It looks effortless. It is not. Behind that instant are dozens of intricate handshakes, lookups, translations, negotiations, and rendering passes — a small symphony performed by your browser, your operating system, several servers, and miles of fiber-optic cable. This explainer walks you through every major act of that symphony, from the keystroke to the interactive page.

---

## Step 1: You Type a URL

Let's start at the very beginning: the address bar. You type something like `https://www.example.com/about`. This string is called a **URL** — Uniform Resource Locator — and it's actually a structured instruction manual with multiple parts.

- **`https`** is the *scheme*, telling the browser which communication protocol to use.
- **`www.example.com`** is the *hostname*, the human-readable name for the computer you want to talk to.
- **`/about`** is the *path*, specifying which specific resource on that computer you want.

Before anything can happen over the network, the browser does a quick check of its own internal state. It looks through its **cache** — a local store of recently fetched pages and assets — to see if it already has a fresh copy of what you're asking for. If the cache contains a valid, unexpired version, the browser can serve it up immediately without going to the network at all. This is why revisiting a page you just left feels nearly instantaneous.

Assuming nothing useful is in cache (or the cached version has expired), the browser needs to talk to the internet. But it can't dial `www.example.com` directly — computers don't understand names. They understand numbers.

---

## Step 2: DNS Resolution — The Internet's Phone Book

Every computer on the internet has a numerical address called an **IP address** — something like `93.184.216.34`. The hostname `www.example.com` is just a convenient alias humans invented so we don't have to memorize numbers. The **Domain Name System**, or DNS, is the infrastructure that translates hostnames back into IP addresses.

Think of DNS like a phone book. You know the person's name (the hostname); DNS looks up their phone number (the IP address) for you.

When your browser needs to look up `www.example.com`, it first asks the operating system, which may already know the answer from a previous lookup stored in its own cache. If not, the OS asks a **recursive resolver** — usually a server run by your ISP or a public service like Google (8.8.8.8) or Cloudflare (1.1.1.1). Your computer was configured to know this resolver's address when it joined the network.

The recursive resolver is like a diligent research librarian. If it doesn't have the answer cached, it goes on a journey:

1. It asks a **root nameserver**: "Who knows about `.com` domains?" The root server doesn't answer the question itself, but it knows who to ask next.
2. The root server responds: "Ask the `.com` TLD nameserver" — the server responsible for all `.com` domains.
3. The resolver asks the `.com` TLD server: "Who's authoritative for `example.com`?"
4. The TLD server responds with the address of Example's own **authoritative nameserver** — the server that actually holds Example's DNS records.
5. The resolver asks that nameserver: "What's the IP for `www.example.com`?"
6. The authoritative server finally answers with the real IP address.

The resolver hands this result back to your browser and also caches it for next time (for a duration specified by the record's **TTL**, or time-to-live). This entire chain typically completes in tens of milliseconds — fast enough to feel invisible, but a real piece of work nonetheless.

---

## Step 3: TCP — Opening a Communication Channel

Now the browser has an IP address. It needs to establish a reliable communication channel to that address. For web traffic, this is done using **TCP** — the Transmission Control Protocol.

TCP is a connection-oriented protocol, meaning before any actual web data flows, the two sides go through a brief ritual to confirm both parties are present and ready. This is called the **three-way handshake**:

1. **SYN**: Your browser sends a packet to the server saying, in effect, "Hello, I'd like to start a conversation. Here's a sequence number I'll use to track my messages."
2. **SYN-ACK**: The server replies: "Got it. I'm here. Here's *my* sequence number. Acknowledging yours."
3. **ACK**: Your browser confirms: "Perfect. Acknowledging yours too. Let's go."

This three-step exchange ensures both sides know the connection is alive and have agreed on the bookkeeping they'll use to keep messages in order. It takes one **round trip** — the time for a packet to travel from your machine to the server and back. Across a typical household internet connection to a server in the same country, a round trip is on the order of 20–60 milliseconds. For a server halfway around the world, it can be 150–300 ms. Doesn't sound like much, but these round trips add up, which is why web engineers obsess over minimizing them.

---

## Step 4: TLS — Sealing the Envelope

Modern web traffic uses HTTPS — the `S` stands for "Secure." Before any web content flows, the browser and server must perform a **TLS handshake** (TLS stands for Transport Layer Security, the successor to SSL). This cryptographic dance does two things: it verifies that the server you connected to is actually who it claims to be, and it negotiates a shared secret key for encrypting everything that follows.

The analogy here is sealing letters in an envelope. Without HTTPS, you're passing postcards anyone along the route can read. HTTPS puts your entire conversation in a locked box that only you and the intended server can open.

Here's a simplified version of how the TLS handshake works with modern TLS 1.3:

1. **ClientHello**: The browser sends a message saying "I'd like to use TLS. Here are the encryption methods I support."
2. **ServerHello + Certificate**: The server picks an encryption method, sends its **digital certificate** (a cryptographically signed document proving its identity, issued by a trusted Certificate Authority like DigiCert or Let's Encrypt), and sends a key-exchange message.
3. **Verification**: Your browser validates the certificate. It checks that the certificate was signed by a CA your browser already trusts (browsers ship with a list of hundreds of trusted root CAs), that the certificate covers the hostname you're visiting, and that the certificate hasn't expired or been revoked.
4. **Key Exchange**: Both sides perform math using the server's public key and some ephemeral values to derive a shared encryption key — without ever transmitting that key directly over the wire. This is the magic of **public-key cryptography**. An eavesdropper watching the packets fly by cannot reconstruct the key, even though they saw all the same messages.
5. **Finished**: Both sides confirm the handshake and switch to encrypted communication.

TLS 1.3 cleverly does all of this in one round trip (older TLS versions took two), keeping the overhead minimal. From this point forward, everything — headers, content, cookies, forms — is encrypted.

---

## Step 5: The HTTP Request

With an encrypted channel open, the browser can finally ask for the page. It does this by sending an **HTTP request**. HTTP (HyperText Transfer Protocol) is the application-layer language browsers and web servers use to communicate. Think of it as a formalized letter format with specific sections.

A simplified HTTP request for `/about` looks like this:

```
GET /about HTTP/2
Host: www.example.com
User-Agent: Mozilla/5.0 ...
Accept: text/html,application/xhtml+xml,...
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9
Cookie: session_id=abc123
```

Breaking that down:

- **`GET /about HTTP/2`** — The *method* (`GET` means "retrieve"), the *path*, and the *protocol version*.
- **`Host`** — Which hostname the request is for. One server can host hundreds of domains on the same IP address; this header tells it which one you want.
- **`User-Agent`** — A description of the browser and OS, so the server can tailor its response.
- **`Accept-Encoding`** — The browser announcing it can handle compressed responses (saving bandwidth).
- **`Cookie`** — Any stored cookies relevant to this site, so the server knows who you are.

HTTP/2 (and the even newer HTTP/3) improves on the original HTTP/1.1 by allowing **multiplexing**: multiple requests and responses can fly back and forth simultaneously over the same connection, rather than queuing up in order. This is a huge performance win, since a modern webpage may request hundreds of separate resources.

---

## Step 6: The Server Processes the Request

The request arrives at the server. But "the server" is itself often a layered system with multiple moving parts.

At the outer edge sits a **reverse proxy or load balancer** — software like Nginx or an AWS load balancer. Its job is to receive incoming requests and route them to the right backend service. For a large site, this single hostname might fan out to dozens or hundreds of application servers running in parallel. The load balancer distributes requests among them to prevent any one machine from being overwhelmed.

Behind the load balancer sits the **web application** — code written in Python, Node.js, Ruby, Java, Go, or another language. This code receives the parsed request, figures out what you're asking for, and generates a response. For the `/about` page, the app might:

1. Check whether you're logged in (reading your session cookie from a database or cache like Redis).
2. Query a **database** (PostgreSQL, MySQL, or similar) for any dynamic content the page needs — maybe a list of team members pulled from a CMS.
3. Run the data through a **template engine** that stitches values into a pre-written HTML skeleton.
4. Return the finished HTML string.

For a static page, there may be no database at all — the server just reads a pre-built HTML file from disk, potentially served through a CDN (Content Delivery Network) edge node that's physically close to you, shaving latency dramatically.

---

## Step 7: The HTTP Response

The server sends back an HTTP response. Like the request, it has a specific structure:

```
HTTP/2 200 OK
Content-Type: text/html; charset=UTF-8
Content-Encoding: gzip
Cache-Control: max-age=3600
Content-Length: 24512

<!DOCTYPE html>
<html>
  <head>...
```

Key parts:

- **`200 OK`** — The **status code**. 200 means success. 404 means "not found." 301 means "moved permanently — go here instead." 500 means the server hit an internal error. There are dozens of status codes, each carrying a specific semantic meaning.
- **`Content-Type`** — Tells the browser what kind of data is coming. `text/html` means the body is an HTML document. If it were an image, this might be `image/png`. This matters: the browser needs to know what it's receiving before it knows how to handle it.
- **`Cache-Control`** — Instructions for caching. `max-age=3600` tells the browser it can reuse this response for up to 3600 seconds (one hour) without re-fetching.
- **`Content-Encoding: gzip`** — The response body has been compressed. The browser will decompress it before processing.

The body of the response is the raw HTML document. The browser starts receiving it, and here is where things get really interesting — because the browser doesn't wait for the entire document to arrive before starting work.

---

## Step 8: HTML Parsing and Building the DOM

As bytes arrive over the network, the browser's **HTML parser** processes them in a streaming fashion, converting the raw text into a tree structure called the **DOM** — the Document Object Model.

Imagine the HTML document as a set of Russian nesting dolls. The outermost doll is the `<html>` element. Inside it are two dolls: `<head>` and `<body>`. Inside `<body>` might be `<header>`, `<main>`, `<footer>`, and so on. Every element in the HTML becomes a **node** in the DOM tree, and the nesting relationships become parent–child relationships in the tree.

This tree is not just a data structure — it's a live, programmable representation of the page. JavaScript can query it, modify it, add and remove nodes at any time. The DOM is the central shared data model that HTML, CSS, and JavaScript all operate on.

Parsing HTML sounds simple but is actually full of edge cases and historical quirks. The HTML specification dedicates enormous effort to exactly how parsers should handle malformed or unexpected markup, because the web accumulated decades of sloppy HTML that browsers learned to tolerate. Unlike XML (which throws errors on malformed input), HTML parsers heroically try to produce something sensible from almost anything.

**A critical detail**: when the parser encounters a `<script>` tag without the `async` or `defer` attributes, it *stops* — it halts parsing the rest of the HTML, fetches the script, executes it, and only then continues parsing. This is because JavaScript can modify the HTML stream itself (via `document.write`), so the parser can't safely look ahead. This is why scripts are traditionally placed at the bottom of the `<body>`, or marked with `defer` or `async`, to avoid blocking the HTML parse.

---

## Step 9: CSS Parsing and Building the CSSOM

Stylesheets are handled in parallel with HTML parsing (where possible). When the parser encounters a `<link rel="stylesheet">` tag, it kicks off a request to fetch that CSS file. When the CSS arrives, the browser's CSS engine parses it into its own tree: the **CSSOM** — CSS Object Model.

The CSSOM stores all the styling rules — colors, fonts, margins, display modes — organized and indexed for efficient lookup. When the browser needs to know "what styles apply to this particular `<p>` element?", it consults the CSSOM.

CSS is powerful but computationally tricky because of **inheritance** and **specificity**. A rule on a parent element can cascade down to children. When multiple rules target the same element, the browser must compute which one wins according to specificity rules (generally: more specific selectors beat less specific ones, and later declarations beat earlier ones when specificity is equal). Modern browsers have highly optimized CSS engines that do this computation extremely quickly.

**Render blocking**: CSS stylesheets are render-blocking. The browser won't paint anything to the screen until the CSSOM is complete, because painting before all styles are known would produce a flash of unstyled content — a visually jarring experience where text and elements briefly appear un-styled before jumping to their final appearance. Loading CSS early, keeping it lean, and using techniques like critical CSS (inlining the styles needed for the initial viewport) are important performance strategies.

---

## Step 10: JavaScript Execution

JavaScript brings the page to life but is also the most complex part of the loading pipeline. A modern JavaScript file is fetched, parsed into an **Abstract Syntax Tree (AST)**, compiled by a **JIT (Just-In-Time) compiler** into machine code, and then executed — all inside the browser's JavaScript engine (V8 in Chrome, SpiderMonkey in Firefox, JavaScriptCore in Safari).

JavaScript runs in the **main thread** — the same thread responsible for parsing HTML and performing layout and paint. This is why expensive JavaScript is so damaging to page performance: while a long script runs, the browser cannot update the screen, causing jank and unresponsiveness.

Modern JavaScript loading strategies:

- **`defer`**: The script is fetched in parallel with HTML parsing, but execution waits until the full HTML document has been parsed. Scripts marked `defer` run in order.
- **`async`**: The script is fetched in parallel and executed as soon as it arrives, without waiting for the parser. Execution order is not guaranteed. Good for independent scripts like analytics.
- **ES modules**: The `type="module"` attribute defers execution by default and enables modern module syntax (`import`/`export`).

JavaScript frameworks like React, Vue, and Angular do significant work during this phase — they parse a virtual description of the UI, reconcile it against the DOM, and potentially rewrite large portions of the tree. **Hydration** (in server-side rendered apps) is the process of attaching event listeners and making static server-rendered HTML interactive. All of this costs CPU time.

---

## Step 11: The Render Tree — Combining DOM and CSSOM

With a complete DOM and a complete CSSOM, the browser constructs the **render tree**: a new tree that contains only the nodes that will actually appear on screen, each annotated with its computed style.

Nodes that don't appear visually — `<head>`, `<script>`, `<meta>`, and anything with `display: none` — are excluded from the render tree. Pseudo-elements like `::before` and `::after` (which exist in CSS but not in the DOM) *are* added to the render tree.

Each visible node in the render tree is called a **render object** (or layout object). It carries its fully computed style: the final pixel values after inheritance, cascading, and relative units have been resolved. `2rem` becomes `32px`. `50%` width becomes `480px` (given a parent of 960px). Colors are resolved from named values to hex or RGB. The render tree is the bridge from the abstract document to the concrete visual representation.

---

## Step 12: Layout — Calculating Where Everything Goes

The render tree tells you *what* to draw but not *where*. The **layout** (also called **reflow**) pass computes the exact position and size of every element on the screen.

Layout is a top-down, recursive process starting from the root of the render tree. The browser walks the tree, computing a **box** for each node — its x and y coordinates, width, and height — based on the CSS box model, the element's computed styles, and the sizes of surrounding elements.

This sounds straightforward, but CSS layout is staggeringly complex. There are multiple layout systems:

- **Block flow**: the traditional stacking of block-level elements top-to-bottom
- **Inline flow**: text and inline elements flowing left-to-right and wrapping
- **Flexbox**: a one-dimensional layout model for flexible rows and columns
- **CSS Grid**: a two-dimensional grid layout system
- **Positioned layout**: elements removed from normal flow and placed absolutely or fixed

Each of these has its own rules, and they can be nested arbitrarily. The browser's layout engine must handle all of them correctly and efficiently. For a rich web application, this computation might need to happen many times per second as the user interacts with the page.

A key optimization: browsers try to perform **incremental layout**, only recalculating the parts of the tree that changed when something is modified, rather than re-laying the entire page from scratch every time.

---

## Step 13: Paint — Drawing Pixels

Layout produces a tree of boxes with precise coordinates. **Paint** is the process of turning those boxes into actual pixels. For each element, the paint stage draws all its visual parts in order: backgrounds, borders, text, images, shadows, outlines.

Painting is done in **layers**. The browser's compositing engine identifies groups of elements that can be painted onto separate surfaces (think of transparent acetate sheets stacked on top of each other). Some elements are automatically promoted to their own layer:

- Elements with `position: fixed`
- Elements animated with `transform` or `opacity`
- Elements with `will-change` hints
- `<video>` and `<canvas>` elements

Why layers? Because if an element on its own layer changes (say, it's being animated), the browser can **repaint just that layer** and **re-composite** the layers together — without touching any of the other layers. This is dramatically cheaper than repainting the entire page.

The paint records are handed off to the **Compositor thread** (separate from the main thread), which rasterizes (converts) them into bitmaps and uploads them to the GPU. The GPU assembles the final frame and pushes it to the display. Modern browsers target 60 frames per second — meaning this entire pipeline (from any JavaScript change to a new frame on screen) must complete in under 16.7 milliseconds.

---

## Step 14: Compositing and the GPU

Modern browsers separate the pipeline into at least two threads: the **main thread** (handles JavaScript, layout, paint records) and the **compositor thread** (handles rasterization and GPU upload). This separation is crucial for smooth scrolling and animation.

When you scroll a webpage, the browser doesn't re-run JavaScript or re-do layout. The compositor thread independently updates which part of the already-painted layer is visible. This is why scrolling tends to feel smooth even on pages with heavy JavaScript — the compositor runs independently and can hit 60fps even if the main thread is briefly busy.

CSS animations and transitions that only change `transform` and `opacity` are similarly handled entirely on the compositor thread, without touching the main thread at all. This is the reason those two properties are performance gold for animation: a bouncing ball animated with `transform: translateX()` costs almost nothing, while animating `left` triggers layout recalculation on every frame.

---

## Step 15: Interactivity — The Page Is Alive

At this point, pixels are on screen and the browser is ready for user interaction. But "interactivity" has a more nuanced meaning than simply "visible."

The browser fires the **`DOMContentLoaded`** event when the HTML has been fully parsed and the initial DOM is ready — scripts marked `defer` have run, but external resources like images or stylesheets may still be loading. JavaScript listening for this event can start manipulating the DOM.

The **`load`** event fires later, once every resource referenced by the page (images, stylesheets, iframes, fonts) has finished loading. Code that needs the page to be fully settled often waits for this event.

**Time to Interactive (TTI)** is a performance metric that measures when the page is not just visually ready but *functionally* ready — when the main thread is no longer blocked, event handlers are registered, and the page can reliably respond to user input. A page can look done but be unresponsive if a large JavaScript bundle is still parsing and executing. This gap between "looks ready" and "is actually ready" is a major source of user frustration on slow connections or low-end devices.

From this point, the page enters its living state: event listeners fire on clicks, hovers, and keystrokes; fetch calls go out to APIs; animations run; the DOM is updated and the render pipeline re-runs for the changed regions. Every interaction potentially triggers a micro-version of the same pipeline — style recalculation, layout, paint, composite — all over again, ideally within a single 16ms frame budget.

---

## The Whole Journey, Compressed

Let's compress the entire journey into a single paragraph:

You hit Enter. The browser checks its cache, fails to find a fresh copy, and asks DNS to translate the hostname into an IP address. It opens a TCP connection with a three-way handshake, then performs a TLS handshake to verify the server's identity and establish encrypted communication. It sends an HTTP request. Somewhere across the internet, a server receives and processes that request — potentially querying a database, rendering a template — and sends back an HTTP response with status code 200 and a gzipped HTML body. The browser decompresses and parses the HTML into a DOM, simultaneously fetching and parsing stylesheets into a CSSOM. JavaScript files are fetched, compiled, and executed. The DOM and CSSOM are combined into a render tree. Layout computes the position and size of every visible element. Paint records how each element should look. The compositor thread rasterizes those records into GPU textures and assembles the final frame. Pixels appear on screen. Event handlers are attached. The page responds to your mouse.

Total elapsed time: often under one second. Frequently under 200 milliseconds for a cached, nearby resource. The engineering effort behind that near-instant response represents decades of protocol design, compiler engineering, graphics pipeline optimization, and distributed systems thinking. Every time you click a link, that entire machine hums to life — silently, swiftly, invisibly — and hands you a page.

---

## Further Threads to Pull

This explainer necessarily simplified many things. If you want to go deeper, each section above has its own rabbit hole:

- **HTTP/3 and QUIC**: The newest version of HTTP runs over UDP instead of TCP, eliminating head-of-line blocking and improving performance on unreliable connections.
- **Service Workers**: JavaScript that runs in the background and can intercept network requests, enabling offline-capable Progressive Web Apps.
- **Content Delivery Networks**: How CDNs cache content geographically close to users to shrink round-trip times from hundreds of milliseconds to single digits.
- **Browser security model**: Same-origin policy, CORS, Content Security Policy, and how browsers prevent malicious pages from stealing your data.
- **Web performance metrics**: Core Web Vitals (LCP, CLS, INP) and how engineers measure and optimize the real user experience of loading.

The web is one of the most complex pieces of engineering that ordinary people interact with daily. The next time a page loads, you'll know a little more about the invisible orchestra playing behind the curtain.

# The World Today — Tuesday, 17 November 2026

A make.fun entry for the **news-image-20261117** bounty: sum up 17 November's
world news in one image.

## What it is

`main.py` is a pure-stdlib Python 3 program (no PIL, no network, no fonts on
disk). It draws a one-page newspaper infographic — masthead, date, and six
story cards with short summaries and small pictogram icons — and writes it to
`/output/entry.png` (1024×1024, well under 1 MiB). The PNG is encoded with
`zlib` + `struct`, and every letter comes from a small 5×7 bitmap font defined
in the program. Running it twice produces byte-identical output.

## The six stories (Tuesday 17 November 2026)

1. **Ukraine hits Crimea's Kerch Bridge again** — a road span fell after a
   second Ukrainian strike in under 24 hours; Russian missiles hit two
   bridges in Kyiv.
2. **Tankers hit by mines near the Strait of Hormuz** — two oil tankers struck
   mines and caught fire; a third US aircraft carrier arrived in the region.
3. **Trump lands in Manila for ASEAN** — Trump arrived in the Philippines for
   the ASEAN summit; China confirmed a first Xi–Trump–Putin meeting for
   Thursday in Shenzhen.
4. **Five EU states plan a Rwanda returns hub** — Germany, Denmark, Austria,
   Greece and the Netherlands announced a joint return facility in Rwanda for
   rejected asylum seekers.
5. **ULA Vulcan rocket fails, 40 Amazon satellites lost** — the rocket failed
   minutes after launch from Cape Canaveral.
6. **JPMorgan blames a software bug for a bank outage** — a bug, not a
   cyberattack, slowed online banking, branches and Zelle payments.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## License

MIT — see `LICENSE`.

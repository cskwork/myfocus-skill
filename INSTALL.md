# Install myfocus

<details>
<summary><strong>Claude Code</strong></summary>

### Install

```bash
claude plugin marketplace add cskwork/myfocus-skill
claude plugin install myfocus@myfocus
```

Type `/myfocus`.

### Verify

```bash
claude plugin list
```

### Update

```bash
claude plugin marketplace update myfocus
```

### Uninstall

```bash
claude plugin uninstall myfocus
claude plugin marketplace remove myfocus
```

</details>

<details>
<summary><strong>Codex</strong></summary>

### Install

```bash
codex plugin marketplace add cskwork/myfocus-skill --ref main
codex plugin add myfocus@myfocus
```

Type `$myfocus`.

### Verify

```bash
codex plugin list
```

### Uninstall

```bash
codex plugin remove myfocus
codex plugin marketplace remove myfocus
```

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

### Install (extension, always-on)

```bash
gemini extensions install https://github.com/cskwork/myfocus-skill
```

### Install (command, opt-in)

```bash
mkdir -p ~/.gemini/commands
curl -fsSL https://raw.githubusercontent.com/cskwork/myfocus-skill/main/skills/myfocus-skill/agents/gemini.toml \
  -o ~/.gemini/commands/myfocus.toml
```

Type `/myfocus` in a new session.

### Verify

```bash
gemini extensions list
```

### Uninstall

```bash
gemini extensions uninstall myfocus
```

</details>

<details>
<summary><strong>Cursor, OpenCode, Amp, and other agent-skills harnesses</strong></summary>

### Install

```bash
npx skills add cskwork/myfocus-skill
npx skills add cskwork/myfocus-skill -g
```

Type `/myfocus` in a new agent chat.

### Verify

```bash
npx skills list
```

### Update

```bash
npx skills update myfocus
```

### Uninstall

```bash
npx skills remove myfocus
```

</details>

<details>
<summary><strong>Antigravity (agy)</strong></summary>

### Install

```bash
agy plugin install https://github.com/cskwork/myfocus-skill
```

### Verify

```bash
agy plugin list
```

### Uninstall

```bash
agy plugin uninstall myfocus
```

</details>

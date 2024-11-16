# check-direct-imports

This hook checks that if both a module is imported and some class/function from that module, always the directly imported symbol is used:

```python
import collections
from collections import defaultdict  # <- directly imported

d = collections.defaultdict(int)  # <- use defaultdict directly!
```

## Additional Arguments

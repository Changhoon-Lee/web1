import Erdos1135.KrasikovLagarias.StreamingCertificate

namespace K19StreamingCanary
open Erdos1135 KrasikovLagarias

/-- Executable tail-loop canary. This is intentionally much smaller than K19. -/
example : NativeRange.allFrom (fun index => decide (index < 100000)) 0 100000 = true := by
  native_decide

example :
    (∀ offset, offset < 100000 →
      (decide (0 + offset < 100000) : Bool) = true) := by
  intro offset hoffset
  simp [hoffset]

end K19StreamingCanary

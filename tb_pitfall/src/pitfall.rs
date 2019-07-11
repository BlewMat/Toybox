use toybox_core;
use toybox_core::random;
use types::*;

use serde_json;
use rand::seq::SliceRandom;

mod screen { 
   pub const SEAFOAM: (u8, u8, u8) = (x, y, z); 
   pub const GROUND_OFFSET: u8 = 14; 
}

impl Pitfall { 
}

impl Default for Pitfall { 
    fn default() -> Self {
       Pitfall {
          // instantiate all of the stuff
      }
    }
}

impl toybox_core::Simulation for Pitfall { 
    fn new_state_from_json(
        &self,
        json_str: &str,
    ) -> Result<Box<toybox_core::State>, serde_json::Error> {
        let state: StateCore = serde_json::from_str(json_str)?;
        Ok(Box::new(State {
            config: self.clone(),
            state,
        }))
    }

    fn from_json(&self, json_str: &str) -> Result<Box<toybox_core::Simulation>, serde_json::Error> {
        let config: Pitfall = serde_json::from_str(json_str)?;
        Ok(Box::new(config))
    }

    fn to_json(&self) -> String {
        serde_json::to_string(self).expect("Pitfall should be JSON-serializable!")
    }
}

impl State { 
} 

impl toybox_core::State for State { 
}

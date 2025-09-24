use scrypto::prelude::*;

blueprint! {
    struct Trivial {}

    impl Trivial {
        pub fn new() -> ComponentAddress {
            Self {}.instantiate().globalize()
        }

        pub fn hello(&self) -> String {
            "hello from trivial blueprint".to_string()
        }
    }
}

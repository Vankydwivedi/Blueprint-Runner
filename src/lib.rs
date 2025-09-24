use scrypto::prelude::*;

#[blueprint]
mod demo_blueprint {
    pub struct DemoBlueprint {
        counter: u64,
    }

    impl DemoBlueprint {
        pub fn new() -> Global<DemoBlueprint> {
            Self { counter: 0 }
                .instantiate()
                .prepare_to_globalize(OwnerRole::None)
                .globalize()
        }

        pub fn increment(&mut self) {
            self.counter += 1;
        }

        pub fn get(&self) -> u64 {
            self.counter
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use scrypto_unit::*;

    #[test]
    fn test_counter_increment() {
        let mut test_env = TestEnvironment::new();
        let component = DemoBlueprint::new();

        test_env.call_method(component, "increment", scrypto_args![]);

        let result: u64 = test_env.call_method(component, "get", scrypto_args![]);

        assert_eq!(result, 1);
    }
}

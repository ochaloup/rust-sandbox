#![allow(dead_code)]
use {
    serde::Deserialize,
    serde::de::{Deserializer, Visitor, MapAccess},
    std::{
        collections::HashMap,
        env,
        fmt::{Debug, Formatter},
        fs::read_to_string,
        marker::PhantomData,
        hash::Hash,
        net::IpAddr,
        path::Path,
        process,
        str::FromStr,
    },
    solana_sdk::pubkey::Pubkey,
};

#[derive(Deserialize, Debug)]
pub struct StakedNodesOverrides {
    pub staked_map_ip: Option<HashMap<IpAddr, u64>>,
    #[serde(default)]
    #[serde(deserialize_with = "simplyfy_deserialize_map")]
    pub staked_map_id: Option<HashMap<Pubkey, u64>>,
}

fn deserialize_full_visitor<'de, D, K, V>(deserializer: D) -> Result<HashMap<K,V>, D::Error>
where
    D: Deserializer<'de>,
    K: Deserialize<'de> + Eq + Hash + FromStr,
    V: Deserialize<'de>,
{
    struct YamlPubkeyMapVisitor<K, V> {
        marker: PhantomData<fn() -> HashMap<K, V>>
    }
    impl<K, V> YamlPubkeyMapVisitor<K, V> {
        fn new() -> Self {
            YamlPubkeyMapVisitor {
                marker: PhantomData
            }
        }
    }

    impl<'de, K, V> Visitor<'de> for YamlPubkeyMapVisitor<K, V>
    where
        K: Deserialize<'de> + Eq + Hash + FromStr,
        V: Deserialize<'de>,
    {
        // The type that our Visitor is going to produce.
        type Value = HashMap<K, V>;

        // Format a message stating what data this Visitor expects to receive.
        fn expecting(&self, formatter: &mut Formatter) -> std::fmt::Result {
            formatter.write_str("a very special map")
        }

        // Deserialize MyMap from an abstract "map" provided by the
        // Deserializer. The MapAccess input is a callback provided by
        // the Deserializer to let us see each entry in the map.
        fn visit_map<M>(self, mut access: M) -> Result<Self::Value, M::Error>
        where
            M: MapAccess<'de>,
        {
            print!("Visiting the map.....");
            let mut map: HashMap<K,V> = HashMap::with_capacity(access.size_hint().unwrap_or(0));

            // While there are entries remaining in the input, add them
            // into our map.
            while let Some((key, value)) = access.next_entry::<&str,V>()? {
                let typed_key: K = K::from_str(key).map_err(|_| {
                    serde::de::Error::invalid_type(serde::de::Unexpected::Map, &"PubKey")
                })?;
                print!("Entry.... {}", key);
                map.insert(typed_key, value);
            }

            Ok(map)
        }
    }

    deserializer.deserialize_map(YamlPubkeyMapVisitor::new())
}

pub fn deserializer_map_keys<'de, T, K, V, D>(des: D) -> Result<T, D::Error>
where
    D: Deserializer<'de>,
    T: FromIterator<(K, V)>,
    K: Deserialize<'de> + Hash + Eq + FromStr,
    V: Deserialize<'de> + Copy,
{
    let container: HashMap<&str,V> = serde::Deserialize::deserialize(des)?;
    let mut container_typed: HashMap<K,V> = HashMap::new();
    for (key, value) in container.iter() {
        let typed_key: K = K::from_str(key).map_err(|_| {
            serde::de::Error::invalid_type(serde::de::Unexpected::Map, &"PubKey")
        })?;
        container_typed.insert(typed_key, *value);
    }
    Ok(T::from_iter(container_typed.into_iter()))
}

pub fn simplyfy_deserialize_map<'de, D>(des: D) -> Result<Option<HashMap<Pubkey,u64>>, D::Error>
    where D: Deserializer<'de> {
    let container: HashMap<&str,u64> = serde::Deserialize::deserialize(des)?;
    let mut container_typed: HashMap<Pubkey,u64> = HashMap::new();
    for (key, value) in container.iter() {
        let typed_key = Pubkey::try_from(*key).map_err(|_| {
            serde::de::Error::invalid_type(serde::de::Unexpected::Map, &"PubKey")
        })?;
        container_typed.insert(typed_key, *value);
    }
    Ok(Some(container_typed))
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() != 2 {
        eprintln!("Expecting one argument but args are: {:?}", args);
        process::exit(1);
    }

    let argument_file = &args[1];
    if !Path::new(argument_file).is_file() {
        eprintln!("Expecting the provided argument being a file path, provided param: '{}'", argument_file);
        process::exit(2);
    }

    let file_content = match read_to_string(argument_file) {
        Err(e) => {
            eprintln!("Expecting the provided argument being a file path '{}': {}", argument_file, e);
            process::exit(3);
        },
        Ok(content) => content,
    };
    // print!("{}", file_content);

    let nodes: StakedNodesOverrides = match serde_yaml::from_str(&file_content.as_str()) {
        Err(e) => {
            eprintln!("Fail to deserialize content {} from {}: {}", file_content, argument_file, e);
            process::exit(4);
        },
        Ok(content) => content,
    };

    print!("{:?}", nodes);
}
